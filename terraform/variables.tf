variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "genapp"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnets" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnets" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.0.3.0/24", "10.0.4.0/24"]
}

variable "azs" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "backend_cpu" {
  description = "ECS backend task CPU units"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "ECS backend task memory (MB)"
  type        = number
  default     = 1024
}

variable "frontend_cpu" {
  description = "ECS frontend task CPU units"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "ECS frontend task memory (MB)"
  type        = number
  default     = 1024
}

variable "github_repo" {
  description = "GitHub repo owner/name — passed automatically by CI/CD via github.repository. For local apply, passed via git remote."
  type        = string
  default     = ""
}
