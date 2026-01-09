# Terraform Implementation Guide

This guide explains how to deploy the GenApp RAG application using Terraform.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform v1.5+
- Docker installed and running

## Project Structure

```
terraform/
├── main.tf          # Provider configuration
├── variables.tf     # Input variables
├── outputs.tf       # Output values
├── vpc.tf           # VPC, subnets, NAT Gateway
├── security.tf      # Security groups, IAM roles
├── cognito.tf       # User Pool, App Client
├── dynamodb.tf      # Chat history table
├── ecs.tf           # ECS cluster, services, ALB
├── rag.tf           # S3, OpenSearch, Bedrock KB
└── terraform.tfvars # Variable values (optional)
```

---

## Step 1: Configure Variables

Edit `variables.tf` or create `terraform.tfvars`:

```hcl
# terraform.tfvars
aws_region   = "us-east-1"
project_name = "genapp"
environment  = "dev"
```

---

## Step 2: Initialize Terraform

```bash
cd terraform
terraform init
```

**Expected output:**
```
Initializing provider plugins...
- Installing hashicorp/aws v5.x.x
Terraform has been successfully initialized!
```

---

## Step 3: Review the Plan

```bash
terraform plan
```

This will show all resources to be created:

| Resource Type | Count |
|---------------|-------|
| VPC & Networking | 12 |
| Security Groups | 2 |
| IAM Roles | 3 |
| ECS Cluster & Services | 5 |
| ECR Repositories | 2 |
| DynamoDB Table | 1 |
| Cognito | 2 |
| OpenSearch Serverless | 4 |
| Bedrock Knowledge Base | 2 |
| **Total** | **~30** |

---

## Step 4: Apply Configuration

```bash
terraform apply -auto-approve
```

**Timeline:**
- VPC, subnets: ~1 minute
- NAT Gateway: ~2 minutes
- OpenSearch Serverless: ~5-10 minutes
- Bedrock Knowledge Base: ~2 minutes
- ECS Services: ~3 minutes

**Total: ~15-20 minutes**

---

## Step 5: Capture Outputs

After successful apply:

```bash
terraform output
```

**Outputs:**
```hcl
alb_dns_name         = "genapp-dev-alb-xxxx.us-east-1.elb.amazonaws.com"
backend_repo_url     = "xxxx.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-backend"
frontend_repo_url    = "xxxx.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-frontend"
cognito_user_pool_id = "us-east-1_xxxxxx"
cognito_client_id    = "xxxxxxxxxxxx"
kb_id                = "XXXXXXXXXX"
s3_bucket_name       = "genapp-dev-docs-xxxx"
dynamodb_table_name  = "genapp-dev-chat-history"
```

---

## Step 6: Build and Push Docker Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Build and push backend
cd ../backend
docker build -t genapp-dev-backend .
docker tag genapp-dev-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-backend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-backend:latest

# Build and push frontend
cd ../frontend
docker build -t genapp-dev-frontend .
docker tag genapp-dev-frontend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-frontend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-frontend:latest
```

---

## Step 7: Force ECS Deployment

```bash
aws ecs update-service --cluster genapp-dev-cluster --service genapp-dev-backend --force-new-deployment
aws ecs update-service --cluster genapp-dev-cluster --service genapp-dev-frontend --force-new-deployment
```

---

## Step 8: Create Test User

```bash
# Create user
aws cognito-idp admin-create-user \
  --user-pool-id <COGNITO_USER_POOL_ID> \
  --username testuser \
  --temporary-password TempPass123!

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id <COGNITO_USER_POOL_ID> \
  --username testuser \
  --password TestPass123! \
  --permanent
```

---

## Terraform File Details

### vpc.tf - Network Infrastructure

```hcl
# Creates:
# - VPC with 10.0.0.0/16 CIDR
# - 2 public subnets (10.0.1.0/24, 10.0.2.0/24)
# - 2 private subnets (10.0.3.0/24, 10.0.4.0/24)
# - Internet Gateway
# - NAT Gateway with Elastic IP
# - Route tables for public and private subnets
```

### security.tf - Security Configuration

```hcl
# Creates:
# - ALB Security Group (port 80 from anywhere)
# - ECS Security Group (8000, 8501 from ALB)
# - ECS Execution Role (ECR, CloudWatch)
# - ECS Task Role (Bedrock, S3, DynamoDB, Cognito)
```

### ecs.tf - Container Orchestration

```hcl
# Creates:
# - ECR repositories (frontend, backend)
# - ECS Cluster
# - Application Load Balancer
# - Target Groups (frontend, backend)
# - Listener with path-based routing
# - Task Definitions
# - ECS Services (Fargate)
```

### rag.tf - RAG Components

```hcl
# Creates:
# - S3 bucket for documents
# - OpenSearch Serverless collection
# - OpenSearch security policies (encryption, network, access)
# - Bedrock Knowledge Base IAM role
# - Bedrock Knowledge Base
# - S3 data source for KB
```

---

## Common Commands

| Command | Purpose |
|---------|---------|
| `terraform init` | Initialize working directory |
| `terraform plan` | Preview changes |
| `terraform apply` | Create/update resources |
| `terraform destroy` | Delete all resources |
| `terraform output` | Show output values |
| `terraform state list` | List managed resources |

---

## Destroy Resources

```bash
cd terraform
terraform destroy -auto-approve
```

**Warning:** This will delete ALL resources including:
- S3 buckets (with all documents)
- DynamoDB tables (with all chat history)
- OpenSearch collection (with all vectors)

---

## Troubleshooting

### OpenSearch Index Creation Fails

The `null_resource.create_index` may fail on first apply. This is normal:

```bash
# Re-run apply
terraform apply -auto-approve
```

### ECS Service Won't Start

Check CloudWatch logs:

```bash
aws logs tail /ecs/genapp-dev-backend --since 10m
aws logs tail /ecs/genapp-dev-frontend --since 10m
```

### Knowledge Base Sync Fails

Ensure IAM role has proper permissions:

```bash
aws bedrock-agent get-knowledge-base --knowledge-base-id <KB_ID>
```
