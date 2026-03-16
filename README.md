# AWS GenAI Architecture Assistant

A multi-agent RAG application that generates professional architecture documents
— HLD, LLD, ADRs, solution designs, risk registers, and more —
using AWS Bedrock, Strands Agents SDK, ECS Fargate, and OpenSearch Serverless.

## Architecture

```
User → ALB → Streamlit (ECS) → FastAPI (ECS) → Strands Orchestrator
                                                      ↓
                              ┌───────────────────────┴──────────────────────┐
                              │         Specialist Agents (Strands)           │
                              │  FR · NFR · BR · Scope · Risk · ADR          │
                              │  HLD · LLD · Components · Diagrams · Assembler│
                              └───────────────────────────────────────────────┘
                                                      ↓
                              Bedrock KB (OpenSearch) · S3 · DynamoDB · Cognito
```

## Features

- **Multi-agent document generation**: 10 specialist agents for every section
- **Intelligent orchestration**: Claude Opus 4.6 decides what to generate
- **Persistent memory**: DynamoDB stores conversation history per session
- **Document download**: Generated docs saved to S3, presigned URL returned
- **JWT auth**: Cognito with automatic token refresh
- **Full IaC**: 100% Terraform managed
- **CI/CD**: GitHub Actions with OIDC (no hardcoded AWS keys)

## Models Used

| Agent | Model | Why |
|-------|-------|-----|
| Orchestrator, HLD, ADR | Claude Opus 4.6 | Deep reasoning for complex architecture |
| FR, NFR, BR, Scope, Risk, LLD, Diagrams | Claude Sonnet 4.6 | Structured output at lower cost |
| Assembler | Claude Haiku 4.5 | Fast formatting and stitching |

## Prerequisites

1. AWS account with admin access
2. GitHub account
3. Terraform v1.5+ installed locally
4. Docker installed locally
5. AWS CLI configured

## Deployment Steps

### Step 1 — Enable Bedrock model access (AWS Console, 2 min)

```
AWS Console → Amazon Bedrock → Model access → Manage model access
Enable: Claude Opus 4.6, Claude Sonnet 4.6, Claude Haiku 4.5
Region: us-east-1
```

### Step 2 — Create Terraform state backend (once)

```bash
# Create S3 bucket for state
aws s3 mb s3://your-terraform-state-bucket --region us-east-1
aws s3api put-bucket-versioning \
  --bucket your-terraform-state-bucket \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Step 3 — Configure Terraform backend

Edit `terraform/providers.tf` and fill in your bucket details:

```hcl
backend "s3" {
  bucket         = "your-terraform-state-bucket"
  key            = "genapp/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "terraform-locks"
  encrypt        = true
}
```

### Step 4 — First local apply (creates OIDC role)

```bash
# Set up git remote first (if not done already)
git remote add origin https://github.com/YOUR-USERNAME/awsgenaiapp.git

# Auto-extract repo name from git remote and apply
cd terraform
terraform init

GITHUB_REPO=$(git -C .. remote get-url origin | sed 's/.*github.com[:/]//' | sed 's/\.git//')
echo "Repo: $GITHUB_REPO"

terraform apply \
  -var="github_repo=$GITHUB_REPO" \
  -auto-approve

# Copy the output
terraform output github_actions_role_arn
```

### Step 5 — Add GitHub secret

```
GitHub repo → Settings → Secrets and variables → Actions → New secret
Name:  AWS_ROLE_ARN
Value: (paste the ARN from Step 4)
```

### Step 6 — Update github_repo variable

Edit `terraform/variables.tf`:
```hcl
variable "github_repo" {
  default = "your-actual-username/awsgenaiapp"
}
```

### Step 7 — Create test user

```bash
POOL_ID=$(cd terraform && terraform output -raw cognito_user_pool_id)

aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username testuser \
  --temporary-password TempPass123!

aws cognito-idp admin-set-user-password \
  --user-pool-id $POOL_ID \
  --username testuser \
  --password MyPass123! \
  --permanent
```

### Step 8 — Push to main

```bash
git add .
git commit -m "Initial deployment"
git push origin main
```

GitHub Actions will:
1. Run `terraform apply` (~15 min for OpenSearch)
2. Build and push Docker images to ECR (with layer caching)
3. Sync reference docs to S3
4. Trigger KB ingestion
5. Force ECS service redeployment
6. Wait for services to stabilise
7. Print the app URL

## Usage

1. Open the app URL from the GitHub Actions output
2. Sign in with your test user credentials
3. Upload a requirements document or meeting notes via the sidebar
4. Wait ~2 minutes for KB indexing
5. Use quick action buttons or type your request:
   - "Generate a complete solution design document"
   - "Generate HLD only"
   - "Generate ADRs for the key decisions"
   - "What are the main risks?"
6. Download the generated document using the button in the chat

## Project Structure

```
awsgenaiapp/
├── .github/workflows/
│   ├── deploy.yml          CI/CD pipeline
│   └── destroy.yml         Manual teardown
├── frontend/
│   ├── app.py              Streamlit UI
│   ├── requirements.txt
│   └── Dockerfile
├── backend/
│   ├── main.py             FastAPI routes
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── tools/
│   │   └── kb_tools.py     Shared @tool functions
│   └── agents/
│       ├── orchestrator.py Opus 4.6 — routes and plans
│       ├── requirements.py FR, NFR, BR agents
│       ├── scope.py        Scope and assumptions
│       ├── risk.py         Risk register + ADRs
│       ├── solution.py     HLD, overview, components
│       ├── detailed.py     LLD, node flow, diagrams
│       └── assembler.py    Haiku 4.5 — merges sections
├── terraform/
│   ├── providers.tf        S3 backend, OIDC
│   ├── variables.tf
│   ├── outputs.tf
│   ├── vpc.tf
│   ├── security.tf         Least-privilege IAM
│   ├── cognito.tf
│   ├── dynamodb.tf         Chat history with TTL
│   ├── ecs.tf              Streamlit + FastAPI
│   ├── rag.tf              KB, OpenSearch, S3
│   └── create_index.py     OpenSearch index creation
├── reference-docs/         Pre-loaded KB content
│   ├── hld-template.md
│   ├── lld-template.md
│   ├── adr-template.md
│   ├── nfr-checklist.md
│   └── solution-template.md
└── README.md
```

## Cost Estimate (dev environment, idle)

| Service | Monthly |
|---------|---------|
| ECS Fargate (2 tasks) | ~$30 |
| ALB | ~$20 |
| NAT Gateway | ~$35 |
| OpenSearch Serverless | ~$50 |
| DynamoDB | ~$1 |
| S3 | ~$1 |
| Bedrock (pay per token) | Usage-based |
| **Total** | **~$137 + usage** |

Use the **Destroy** workflow to tear down all resources when not in use.

## Destroy Resources

Go to GitHub → Actions → Destroy GenApp → Run workflow → type `DESTROY`

## Troubleshooting

**ECS tasks not starting:**
```bash
aws logs tail /ecs/genapp-dev-backend --since 10m
aws logs tail /ecs/genapp-dev-frontend --since 10m
```

**KB ingestion failing:**
```bash
aws bedrock-agent get-knowledge-base --knowledge-base-id <KB_ID>
```

**Agents returning empty results:**
- Check documents are uploaded to `uploads/` or `reference/` S3 prefix
- Confirm KB ingestion job completed (takes 2-10 min)
- Verify Bedrock model access is enabled for all 3 Claude models
