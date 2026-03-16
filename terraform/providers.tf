terraform {
  required_version = ">= 1.5, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Fill these in before first apply:
    # bucket         = "your-terraform-state-bucket"
    # key            = "genapp/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "your-terraform-locks-table"
    # encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
