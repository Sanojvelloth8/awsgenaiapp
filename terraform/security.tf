# ALB Security Group
resource "aws_security_group" "alb" {
  name   = "${var.project_name}-${var.environment}-alb-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ECS Security Group
resource "aws_security_group" "ecs" {
  name   = "${var.project_name}-${var.environment}-ecs-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ECS Execution Role
resource "aws_iam_role" "execution" {
  name = "${var.project_name}-${var.environment}-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# CloudWatch Logs for ECS tasks
resource "aws_iam_role_policy_attachment" "execution_logs" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# ECS Task Role (for application permissions)
resource "aws_iam_role" "task" {
  name = "${var.project_name}-${var.environment}-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

# Bedrock Full Access
resource "aws_iam_role_policy_attachment" "bedrock" {
  role       = aws_iam_role.task.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

# S3 Full Access (for presigned URLs generation)
resource "aws_iam_role_policy_attachment" "s3" {
  role       = aws_iam_role.task.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# DynamoDB Full Access
resource "aws_iam_role_policy_attachment" "dynamodb" {
  role       = aws_iam_role.task.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

# Cognito for auth from frontend
resource "aws_iam_role_policy_attachment" "cognito" {
  role       = aws_iam_role.task.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonCognitoPowerUser"
}
