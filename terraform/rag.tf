# S3 Bucket for Documents
resource "aws_s3_bucket" "docs" {
  bucket_prefix = "${var.project_name}-${var.environment}-docs-"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = aws_s3_bucket.docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# OpenSearch Serverless
resource "aws_opensearchserverless_security_policy" "enc" {
  name = "${var.project_name}-${var.environment}-enc"
  type = "encryption"
  policy = jsonencode({
    Rules = [{ ResourceType = "collection", Resource = ["collection/${var.project_name}-${var.environment}-vec"] }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "net" {
  name = "${var.project_name}-${var.environment}-net"
  type = "network"
  policy = jsonencode([{
    Rules = [
      { ResourceType = "collection", Resource = ["collection/${var.project_name}-${var.environment}-vec"] },
      { ResourceType = "dashboard", Resource = ["collection/${var.project_name}-${var.environment}-vec"] }
    ]
    AllowFromPublic = true
  }])
}

data "aws_caller_identity" "current" {}

resource "aws_opensearchserverless_access_policy" "data" {
  name = "${var.project_name}-${var.environment}-access"
  type = "data"
  policy = jsonencode([{
    Rules = [
      { ResourceType = "collection", Resource = ["collection/${var.project_name}-${var.environment}-vec"], Permission = ["aoss:CreateCollectionItems", "aoss:DeleteCollectionItems", "aoss:UpdateCollectionItems", "aoss:DescribeCollectionItems"] },
      { ResourceType = "index", Resource = ["index/${var.project_name}-${var.environment}-vec/*"], Permission = ["aoss:CreateIndex", "aoss:DeleteIndex", "aoss:UpdateIndex", "aoss:DescribeIndex", "aoss:ReadDocument", "aoss:WriteDocument"] }
    ]
    Principal = [data.aws_caller_identity.current.arn, aws_iam_role.bedrock_kb.arn]
  }])
}

resource "aws_opensearchserverless_collection" "main" {
  name             = "${var.project_name}-${var.environment}-vec"
  type             = "VECTORSEARCH"
  standby_replicas = "DISABLED"
  depends_on       = [aws_opensearchserverless_security_policy.enc]
}

# Bedrock KB Role
resource "aws_iam_role" "bedrock_kb" {
  name = "${var.project_name}-${var.environment}-kb-role-new"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*" }
      }
    }]
  })
}

resource "aws_iam_role_policy" "kb_s3" {
  name = "s3-access"
  role = aws_iam_role.bedrock_kb.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["s3:ListBucket", "s3:GetObject"], Resource = [aws_s3_bucket.docs.arn, "${aws_s3_bucket.docs.arn}/*"] }]
  })
}

resource "aws_iam_role_policy" "kb_aoss" {
  name = "aoss-access"
  role = aws_iam_role.bedrock_kb.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["aoss:APIAccessAll"], Resource = [aws_opensearchserverless_collection.main.arn] }]
  })
}

resource "aws_iam_role_policy" "kb_model" {
  name = "model-access"
  role = aws_iam_role.bedrock_kb.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = ["arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v1"] }]
  })
}

# Bedrock Knowledge Base
# First create the index using a local provisioner
resource "null_resource" "create_index" {
  depends_on = [
    aws_opensearchserverless_collection.main,
    aws_opensearchserverless_access_policy.data
  ]

  provisioner "local-exec" {
    command = "pip3 install opensearch-py requests-aws4auth -q && python3 create_index.py ${aws_opensearchserverless_collection.main.collection_endpoint} default-index ${var.aws_region}"
    working_dir = path.module
  }
}

resource "aws_bedrockagent_knowledge_base" "main" {
  name     = "${var.project_name}-${var.environment}-kb"
  role_arn = aws_iam_role.bedrock_kb.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v1"
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.main.arn
      vector_index_name = "default-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }

  depends_on = [
    null_resource.create_index,
    aws_opensearchserverless_access_policy.data,
    aws_opensearchserverless_security_policy.net,
    aws_opensearchserverless_collection.main,
    aws_iam_role_policy.kb_aoss
  ]
}

resource "aws_bedrockagent_data_source" "s3" {
  knowledge_base_id    = aws_bedrockagent_knowledge_base.main.id
  name                 = "${var.project_name}-${var.environment}-s3-ds"
  data_deletion_policy = "RETAIN"
  data_source_configuration {
    type = "S3"
    s3_configuration { bucket_arn = aws_s3_bucket.docs.arn }
  }
}
