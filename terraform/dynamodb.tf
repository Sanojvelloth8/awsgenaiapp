# DynamoDB Table for Chat History
resource "aws_dynamodb_table" "chat" {
  name         = "${var.project_name}-${var.environment}-chat-history"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  range_key    = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.chat.name
}
