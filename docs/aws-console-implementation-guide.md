# AWS Console Implementation Guide

This document provides **step-by-step instructions** to deploy the GenApp RAG application using the **AWS Management Console (GUI)**. Follow each section in order to create all required components.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Networking (VPC)](#phase-1-networking-vpc)
3. [Phase 2: Security](#phase-2-security)
4. [Phase 3: Storage & Database](#phase-3-storage--database)
5. [Phase 4: Authentication (Cognito)](#phase-4-authentication-cognito)
6. [Phase 5: AI/ML Stack (Bedrock & OpenSearch)](#phase-5-aiml-stack-bedrock--opensearch)
7. [Phase 6: Container Registry (ECR)](#phase-6-container-registry-ecr)
8. [Phase 7: Container Orchestration (ECS)](#phase-7-container-orchestration-ecs)
9. [Phase 8: Load Balancer (ALB)](#phase-8-load-balancer-alb)
10. [Phase 9: Deploy Application](#phase-9-deploy-application)
11. [Phase 10: Testing & Validation](#phase-10-testing--validation)

---

## Prerequisites

Before starting, ensure you have:

- [ ] AWS Account with Administrator access
- [ ] AWS Region: **us-east-1** (N. Virginia) - Bedrock is available here
- [ ] Docker installed locally for building container images
- [ ] AWS CLI configured with credentials

---

## Phase 1: Networking (VPC)

### Step 1.1: Create VPC.

1. Navigate to **VPC Console** → [https://console.aws.amazon.com/vpc](https://console.aws.amazon.com/vpc)
2. Click **"Create VPC"**
3. Select **"VPC and more"** (wizard mode)
4. Configure:

| Setting | Value |
|---------|-------|
| Name tag auto-generation | `genapp-dev` |
| IPv4 CIDR block | `10.0.0.0/16` |
| IPv6 CIDR block | No IPv6 |
| Tenancy | Default |
| Number of Availability Zones | `2` |
| Number of public subnets | `2` |
| Number of private subnets | `2` |
| NAT gateways | `In 1 AZ` (cost-effective) |
| VPC endpoints | None |

5. Click **"Create VPC"**
6. Wait for all resources to be created (2-3 minutes)

### Verification Checklist
- [ ] VPC created: `genapp-dev-vpc`
- [ ] 2 Public subnets: `10.0.0.0/20`, `10.0.16.0/20`
- [ ] 2 Private subnets: `10.0.128.0/20`, `10.0.144.0/20`
- [ ] 1 Internet Gateway attached
- [ ] 1 NAT Gateway in public subnet
- [ ] Route tables configured

---

## Phase 2: Security

### Step 2.1: Create ALB Security Group

1. Navigate to **EC2 Console** → **Security Groups**
2. Click **"Create security group"**
3. Configure:

| Setting | Value |
|---------|-------|
| Security group name | `genapp-dev-alb-sg` |
| Description | `Security group for Application Load Balancer` |
| VPC | Select `genapp-dev-vpc` |

4. **Inbound rules** - Click "Add rule":

| Type | Port Range | Source | Description |
|------|------------|--------|-------------|
| HTTP | 80 | `0.0.0.0/0` | Allow HTTP from internet |
| HTTPS | 443 | `0.0.0.0/0` | Allow HTTPS from internet (optional) |

5. **Outbound rules** - Keep default (All traffic)
6. Click **"Create security group"**

---

### Step 2.2: Create ECS Security Group

1. Click **"Create security group"**
2. Configure:

| Setting | Value |
|---------|-------|
| Security group name | `genapp-dev-ecs-sg` |
| Description | `Security group for ECS Fargate tasks` |
| VPC | Select `genapp-dev-vpc` |

3. **Inbound rules** - Click "Add rule":

| Type | Port Range | Source | Description |
|------|------------|--------|-------------|
| All traffic | All | `genapp-dev-alb-sg` | Allow from ALB only |

4. **Outbound rules** - Keep default (All traffic - needed for AWS API calls)
5. Click **"Create security group"**

---

### Step 2.3: Create Required IAM Roles

#### 2.3.1 ECS Task Execution Role

1. Navigate to **IAM Console** → [https://console.aws.amazon.com/iam](https://console.aws.amazon.com/iam)
2. Click **"Roles"** → **"Create role"**
3. Configure:

| Setting | Value |
|---------|-------|
| Trusted entity type | AWS service |
| Use case | Elastic Container Service |
| Use case | Elastic Container Service Task |

4. Click **"Next"**
5. Search and attach these policies:
   - `AmazonECSTaskExecutionRolePolicy`
   - `CloudWatchLogsFullAccess`
6. Click **"Next"**
7. Role name: `genapp-dev-execution-role`
8. Click **"Create role"**

---

#### 2.3.2 ECS Task Role (Application Permissions)

1. Click **"Create role"**
2. Configure same as above (ECS Task)
3. Attach these policies:
   - `AmazonBedrockFullAccess`
   - `AmazonS3FullAccess`
   - `AmazonDynamoDBFullAccess`
   - `AmazonCognitoPowerUser`
4. Role name: `genapp-dev-task-role`
5. Click **"Create role"**

---

#### 2.3.3 Bedrock Knowledge Base Role

1. Click **"Create role"**
2. Select **"Custom trust policy"**
3. Paste this trust policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "YOUR_ACCOUNT_ID"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:knowledge-base/*"
                }
            }
        }
    ]
}
```

> [!IMPORTANT]
> Replace `YOUR_ACCOUNT_ID` with your 12-digit AWS Account ID

4. Click **"Next"**
5. Skip policy attachment for now
6. Role name: `genapp-dev-kb-role`
7. Click **"Create role"**
8. Open the role → **"Add permissions"** → **"Create inline policy"**
9. Switch to **JSON** tab and paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:ListBucket", "s3:GetObject"],
            "Resource": ["arn:aws:s3:::genapp-dev-docs-*", "arn:aws:s3:::genapp-dev-docs-*/*"]
        },
        {
            "Effect": "Allow",
            "Action": ["aoss:APIAccessAll"],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel"],
            "Resource": ["arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"]
        }
    ]
}
```

10. Policy name: `kb-access-policy`
11. Click **"Create policy"**

---

## Phase 3: Storage & Database

### Step 3.1: Create S3 Bucket for Documents

1. Navigate to **S3 Console** → [https://console.aws.amazon.com/s3](https://console.aws.amazon.com/s3)
2. Click **"Create bucket"**
3. Configure:

| Setting | Value |
|---------|-------|
| Bucket name | `genapp-dev-docs-UNIQUE_SUFFIX` (must be globally unique) |
| AWS Region | `us-east-1` |
| Object Ownership | ACLs disabled |
| Block all public access | ✅ Enabled (all 4 checkboxes) |
| Bucket Versioning | Disabled |
| Default encryption | SSE-S3 |

4. Click **"Create bucket"**

> [!NOTE]
> Note down the bucket name - you'll need it for Bedrock Knowledge Base

---

### Step 3.2: Create DynamoDB Table for Chat History

1. Navigate to **DynamoDB Console** → [https://console.aws.amazon.com/dynamodb](https://console.aws.amazon.com/dynamodb)
2. Click **"Create table"**
3. Configure:

| Setting | Value |
|---------|-------|
| Table name | `genapp-dev-chat-history` |
| Partition key | `session_id` (String) |
| Sort key | `timestamp` (Number) |
| Table settings | Customize settings |
| Table class | DynamoDB Standard |
| Read/write capacity settings | On-demand |

4. Click **"Create table"**
5. After creation, go to **"Additional settings"** tab
6. Enable **TTL**:
   - Click **"Turn on"**
   - TTL attribute name: `ttl`
   - Click **"Turn on TTL"**

---

## Phase 4: Authentication (Cognito)

### Step 4.1: Create User Pool

1. Navigate to **Cognito Console** → [https://console.aws.amazon.com/cognito](https://console.aws.amazon.com/cognito)
2. Click **"Create user pool"**

#### Step 1 - Sign-in experience
| Setting | Value |
|---------|-------|
| Provider types | Cognito user pool |
| Sign-in options | ✅ Email |

Click **"Next"**

#### Step 2 - Security requirements
| Setting | Value |
|---------|-------|
| Password policy mode | Cognito defaults |
| MFA enforcement | No MFA |
| User account recovery | ✅ Enable self-service (Email only) |

Click **"Next"**

#### Step 3 - Sign-up experience
| Setting | Value |
|---------|-------|
| Self-registration | ✅ Enable |
| Attribute verification | ✅ Email |
| Required attributes | email |

Click **"Next"**

#### Step 4 - Message delivery
| Setting | Value |
|---------|-------|
| Email provider | Send email with Cognito |
| FROM email address | no-reply@verificationemail.com |

Click **"Next"**

#### Step 5 - Integrate your app
| Setting | Value |
|---------|-------|
| User pool name | `genapp-dev-users` |
| Hosted authentication pages | ❌ Uncheck (not needed) |
| App type | Public client |
| App client name | `genapp-dev-client` |
| Client secret | Don't generate |
| Authentication flows | ✅ ALLOW_USER_PASSWORD_AUTH, ✅ ALLOW_REFRESH_TOKEN_AUTH, ✅ ALLOW_USER_SRP_AUTH |

Click **"Next"** → **"Create user pool"**

---

### Step 4.2: Create Test User

1. Open your user pool `genapp-dev-users`
2. Go to **"Users"** tab
3. Click **"Create user"**
4. Configure:

| Setting | Value |
|---------|-------|
| Invitation message | Don't send |
| User name | `testuser` |
| Email address | `your-email@example.com` |
| Temporary password | Set a password |
| Mark email as verified | ✅ Yes |

5. Click **"Create user"**

> [!IMPORTANT]
> Note down:
> - **User Pool ID**: `us-east-1_XXXXXXXX`
> - **App Client ID**: `XXXXXXXXXXXXXXXXXXXXXXXXXX`
> 
> You'll need these for the frontend configuration.

---

## Phase 5: AI/ML Stack (Bedrock & OpenSearch)

### Step 5.1: Enable Bedrock Model Access

1. Navigate to **Bedrock Console** → [https://console.aws.amazon.com/bedrock](https://console.aws.amazon.com/bedrock)
2. In the left sidebar, click **"Model access"** (under Bedrock configurations)
3. Click **"Manage model access"** or **"Modify model access"**
4. Enable these models:
   - ✅ **Amazon Titan Text G1 - Express** (for text generation)
   - ✅ **Amazon Titan Embeddings G1 - Text** (for embedding)
5. Click **"Request model access"** or **"Save changes"**
6. Wait for status to show "Access granted" (usually instant for Amazon models)

---

### Step 5.2: Create OpenSearch Serverless Collection

1. Navigate to **OpenSearch Console** → [https://console.aws.amazon.com/aos](https://console.aws.amazon.com/aos)
2. In left sidebar, click **"Serverless"** → **"Collections"**
3. Click **"Create collection"**

#### Collection settings
| Setting | Value |
|---------|-------|
| Collection name | `genapp-dev-vec` |
| Collection type | **Vector search** |
| Security | Easy create ✅ |
| Standby replicas | ❌ Disable (cost saving) |

4. Click **"Next"**

#### Network access
| Setting | Value |
|---------|-------|
| Access type | Public |

5. Click **"Next"** → **"Create"**

6. Wait for collection status to become **"Active"** (5-10 minutes)

> [!IMPORTANT]
> Note down the **Collection Endpoint URL**: `https://XXXXXXXXXX.us-east-1.aoss.amazonaws.com`

---

### Step 5.3: Create Vector Index

After the collection is active, you need to create an index. This requires running a script:

1. Open **CloudShell** (top-right of AWS Console) or use local terminal
2. Run:

```bash
pip3 install opensearch-py requests-aws4auth

python3 << 'EOF'
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Configuration
region = 'us-east-1'
host = 'YOUR_COLLECTION_ENDPOINT'  # e.g., 'abc123.us-east-1.aoss.amazonaws.com'
index_name = 'default-index'

# Auth
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'aoss', session_token=credentials.token)

# Connect
client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    connection_class=RequestsHttpConnection,
    timeout=60
)

# Create index
body = {
    "settings": {
        "index.knn": True
    },
    "mappings": {
        "properties": {
            "bedrock-knowledge-base-default-vector": {
                "type": "knn_vector",
                "dimension": 1536,
                "method": {"name": "hnsw", "engine": "faiss", "parameters": {"ef_construction": 512, "m": 16}}
            },
            "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
            "AMAZON_BEDROCK_METADATA": {"type": "text"}
        }
    }
}

client.indices.create(index=index_name, body=body)
print(f"Index '{index_name}' created successfully!")
EOF
```

> [!IMPORTANT]
> Replace `YOUR_COLLECTION_ENDPOINT` with your actual endpoint (without `https://`)

---

### Step 5.4: Create Bedrock Knowledge Base

1. Navigate to **Bedrock Console** → **"Knowledge bases"** (left sidebar under Builder tools)
2. Click **"Create knowledge base"**

#### Step 1 - Knowledge base details
| Setting | Value |
|---------|-------|
| Knowledge base name | `genapp-dev-kb` |
| Description | `RAG Knowledge Base for GenApp` |
| IAM role | Choose existing → `genapp-dev-kb-role` |

Click **"Next"**

#### Step 2 - Data source
| Setting | Value |
|---------|-------|
| Data source name | `genapp-dev-s3-ds` |
| S3 URI | Browse and select your bucket `s3://genapp-dev-docs-XXXXX` |

Click **"Next"**

#### Step 3 - Embeddings and Vector store
| Setting | Value |
|---------|-------|
| Embeddings model | **Titan Embeddings G1 - Text** |
| Vector database | **Amazon OpenSearch Serverless** |
| Choose an existing vector store | ✅ |
| Select collection | `genapp-dev-vec` |
| Vector index name | `default-index` |
| Vector field name | `bedrock-knowledge-base-default-vector` |
| Text field name | `AMAZON_BEDROCK_TEXT_CHUNK` |
| Metadata field name | `AMAZON_BEDROCK_METADATA` |

Click **"Next"** → **"Create knowledge base"**

> [!IMPORTANT]
> Note down the **Knowledge Base ID**: `XXXXXXXXXX`

---

## Phase 6: Container Registry (ECR)

### Step 6.1: Create Backend Repository

1. Navigate to **ECR Console** → [https://console.aws.amazon.com/ecr](https://console.aws.amazon.com/ecr)
2. Click **"Create repository"**
3. Configure:

| Setting | Value |
|---------|-------|
| Visibility | Private |
| Repository name | `genapp-dev-backend` |
| Tag immutability | Disabled |
| Scan on push | Enabled |

4. Click **"Create"**

---

### Step 6.2: Create Frontend Repository

1. Click **"Create repository"**
2. Repository name: `genapp-dev-frontend`
3. Keep other settings same
4. Click **"Create"**

> [!NOTE]
> Note the repository URIs:
> - `ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-backend`
> - `ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-frontend`

---

## Phase 7: Container Orchestration (ECS)

### Step 7.1: Create ECS Cluster

1. Navigate to **ECS Console** → [https://console.aws.amazon.com/ecs](https://console.aws.amazon.com/ecs)
2. Click **"Create cluster"**
3. Configure:

| Setting | Value |
|---------|-------|
| Cluster name | `genapp-dev-cluster` |
| Infrastructure | AWS Fargate (serverless) |

4. Click **"Create"**

---

### Step 7.2: Create Backend Task Definition

1. Go to **"Task definitions"** → **"Create new task definition"**
2. Select **"Create new task definition with JSON"**
3. Paste:

```json
{
    "family": "genapp-dev-backend",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "256",
    "memory": "512",
    "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/genapp-dev-execution-role",
    "taskRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/genapp-dev-task-role",
    "containerDefinitions": [
        {
            "name": "backend",
            "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-backend:latest",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "hostPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "AWS_REGION", "value": "us-east-1"},
                {"name": "DYNAMODB_TABLE", "value": "genapp-dev-chat-history"},
                {"name": "KB_ID", "value": "YOUR_KB_ID"},
                {"name": "KB_BUCKET_NAME", "value": "YOUR_BUCKET_NAME"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/genapp-dev-backend",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs",
                    "awslogs-create-group": "true"
                }
            },
            "essential": true
        }
    ]
}
```

> [!IMPORTANT]
> Replace:
> - `YOUR_ACCOUNT_ID` - Your 12-digit AWS Account ID
> - `YOUR_KB_ID` - Bedrock Knowledge Base ID
> - `YOUR_BUCKET_NAME` - S3 Bucket name

4. Click **"Create"**

---

### Step 7.3: Create Frontend Task Definition

1. **"Create new task definition with JSON"**
2. Paste:

```json
{
    "family": "genapp-dev-frontend",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "256",
    "memory": "512",
    "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/genapp-dev-execution-role",
    "taskRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/genapp-dev-task-role",
    "containerDefinitions": [
        {
            "name": "frontend",
            "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/genapp-dev-frontend:latest",
            "portMappings": [
                {
                    "containerPort": 8501,
                    "hostPort": 8501,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "BACKEND_URL", "value": "http://YOUR_ALB_DNS"},
                {"name": "COGNITO_USER_POOL_ID", "value": "YOUR_USER_POOL_ID"},
                {"name": "COGNITO_CLIENT_ID", "value": "YOUR_CLIENT_ID"},
                {"name": "AWS_REGION", "value": "us-east-1"}
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/genapp-dev-frontend",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs",
                    "awslogs-create-group": "true"
                }
            },
            "essential": true
        }
    ]
}
```

> [!NOTE]
> `YOUR_ALB_DNS` will be updated after creating the ALB.

---

## Phase 8: Load Balancer (ALB)

### Step 8.1: Create Application Load Balancer

1. Navigate to **EC2 Console** → **Load Balancers**
2. Click **"Create load balancer"** → **Application Load Balancer**
3. Configure:

#### Basic configuration
| Setting | Value |
|---------|-------|
| Load balancer name | `genapp-dev-alb` |
| Scheme | Internet-facing |
| IP address type | IPv4 |

#### Network mapping
| Setting | Value |
|---------|-------|
| VPC | `genapp-dev-vpc` |
| Mappings | Select **both public subnets** (us-east-1a, us-east-1b) |

#### Security groups
- Remove default security group
- Add `genapp-dev-alb-sg`

#### Listeners and routing
| Setting | Value |
|---------|-------|
| Protocol | HTTP |
| Port | 80 |
| Default action | Create target group (next step) |

4. Click **"Create target group"** link (opens new tab)

---

### Step 8.2: Create Frontend Target Group

1. Configure:

| Setting | Value |
|---------|-------|
| Target type | IP addresses |
| Target group name | `genapp-dev-fe-tg` |
| Protocol | HTTP |
| Port | 8501 |
| VPC | `genapp-dev-vpc` |

#### Health checks
| Setting | Value |
|---------|-------|
| Protocol | HTTP |
| Path | `/` |
| Success codes | `200-399` |

2. Click **"Next"** → Skip registering targets → **"Create target group"**

---

### Step 8.3: Create Backend Target Group

1. Create another target group:

| Setting | Value |
|---------|-------|
| Target group name | `genapp-dev-be-tg` |
| Port | 8000 |
| Health check path | `/` |
| Success codes | `200-404` |

2. Create the target group

---

### Step 8.4: Complete ALB Creation

1. Go back to ALB creation tab
2. Refresh and select `genapp-dev-fe-tg` as default action
3. Click **"Create load balancer"**

---

### Step 8.5: Add API Listener Rule

1. Open your ALB → **"Listeners"** tab
2. Click on the HTTP:80 listener → **"View/edit rules"**
3. Click **"Add rules"** → **"Add rule"**
4. Configure:

| Setting | Value |
|---------|-------|
| Name | `api-routing` |
| Priority | 100 |

**Conditions:**
- Path pattern: `/api/*`, `/docs`, `/openapi.json`

**Actions:**
- Forward to: `genapp-dev-be-tg`

5. Click **"Create"**

> [!IMPORTANT]
> Note down the **ALB DNS Name**: `genapp-dev-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com`

---

## Phase 9: Deploy Application

### Step 9.1: Build and Push Docker Images

Run these commands on your local machine:

```bash
# Set variables
export AWS_REGION=us-east-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push backend
cd backend
docker build -t genapp-dev-backend .
docker tag genapp-dev-backend:latest $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/genapp-dev-backend:latest
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/genapp-dev-backend:latest

# Build and push frontend
cd ../frontend
docker build -t genapp-dev-frontend .
docker tag genapp-dev-frontend:latest $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/genapp-dev-frontend:latest
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/genapp-dev-frontend:latest
```

---

### Step 9.2: Update Frontend Task Definition

1. Go to **ECS Console** → **Task Definitions** → `genapp-dev-frontend`
2. Click **"Create new revision"**
3. Update `BACKEND_URL` environment variable with your ALB DNS:
   - `http://genapp-dev-alb-XXXXXXXXX.us-east-1.elb.amazonaws.com`
4. Click **"Create"**

---

### Step 9.3: Create Backend Service

1. Go to **ECS Console** → **Clusters** → `genapp-dev-cluster`
2. Click **"Services"** tab → **"Create"**
3. Configure:

#### Environment
| Setting | Value |
|---------|-------|
| Launch type | FARGATE |

#### Deployment configuration
| Setting | Value |
|---------|-------|
| Task definition family | `genapp-dev-backend` |
| Revision | LATEST |
| Service name | `genapp-dev-backend` |
| Desired tasks | 1 |

#### Networking
| Setting | Value |
|---------|-------|
| VPC | `genapp-dev-vpc` |
| Subnets | Select **both private subnets** |
| Security group | `genapp-dev-ecs-sg` |
| Public IP | Off |

#### Load balancing
| Setting | Value |
|---------|-------|
| Type | Application Load Balancer |
| Load balancer | `genapp-dev-alb` |
| Container | `backend:8000` |
| Target group | `genapp-dev-be-tg` |

4. Click **"Create"**

---

### Step 9.4: Create Frontend Service

1. Click **"Create"** service again
2. Configure same as backend except:

| Setting | Value |
|---------|-------|
| Task definition | `genapp-dev-frontend` |
| Service name | `genapp-dev-frontend` |
| Container | `frontend:8501` |
| Target group | `genapp-dev-fe-tg` |

3. Click **"Create"**

---

## Phase 10: Testing & Validation

### Step 10.1: Wait for Services to Start

1. Go to **ECS Console** → **Clusters** → `genapp-dev-cluster`
2. Check both services show **"Running: 1"**
3. Check target groups are **"healthy"** in EC2 → Target Groups

---

### Step 10.2: Access the Application

1. Open your browser
2. Navigate to: `http://YOUR_ALB_DNS_NAME`
3. You should see the **Login page**

---

### Step 10.3: Test Login

1. Enter username and password (from Cognito test user)
2. Click **Login**
3. You should see the **Chat interface**

---

### Step 10.4: Test Document Upload

1. In the sidebar, click **"Upload Document"**
2. Select a PDF or TXT file
3. Click **"Upload"**
4. Wait for sync to complete

---

### Step 10.5: Test RAG Query

1. Type a question related to your uploaded document
2. Verify the answer references the document sources

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| ECS service stuck in PENDING | Check CloudWatch logs, verify IAM roles |
| Target group unhealthy | Check security group allows ALB traffic |
| Bedrock 403 error | Verify model access is enabled |
| Cognito login fails | Verify user is confirmed, check client ID |
| No sources returned | Upload document and trigger sync |

### Useful CloudWatch Log Groups

- `/ecs/genapp-dev-backend` - Backend logs
- `/ecs/genapp-dev-frontend` - Frontend logs

---

## Clean Up

To delete all resources:

1. **ECS Services** - Set desired count to 0, then delete
2. **ECS Cluster** - Delete cluster
3. **ECR Repositories** - Delete images, then repositories
4. **ALB & Target Groups** - Delete ALB, then target groups
5. **Bedrock Knowledge Base** - Delete KB, then data source
6. **OpenSearch Serverless** - Delete collection
7. **DynamoDB** - Delete table
8. **S3** - Empty bucket, then delete
9. **Cognito** - Delete user pool
10. **IAM Roles** - Delete custom roles
11. **VPC** - Delete VPC (will remove subnets, gateways, etc.)

> [!CAUTION]
> OpenSearch Serverless collections incur charges even when idle. Delete promptly if not in use.

---

## Summary of Resources Created

| Resource | Name | Console Link |
|----------|------|--------------|
| VPC | genapp-dev-vpc | [VPC Console](https://console.aws.amazon.com/vpc) |
| ALB | genapp-dev-alb | [EC2 Load Balancers](https://console.aws.amazon.com/ec2/v2/home#LoadBalancers:) |
| ECS Cluster | genapp-dev-cluster | [ECS Console](https://console.aws.amazon.com/ecs) |
| DynamoDB | genapp-dev-chat-history | [DynamoDB Console](https://console.aws.amazon.com/dynamodb) |
| S3 | genapp-dev-docs-* | [S3 Console](https://console.aws.amazon.com/s3) |
| Cognito | genapp-dev-users | [Cognito Console](https://console.aws.amazon.com/cognito) |
| Bedrock KB | genapp-dev-kb | [Bedrock Console](https://console.aws.amazon.com/bedrock) |
| OpenSearch | genapp-dev-vec | [OpenSearch Console](https://console.aws.amazon.com/aos) |
