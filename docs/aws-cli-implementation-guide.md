# AWS CLI Implementation Guide

This guide provides step-by-step AWS CLI commands to deploy the GenApp RAG application

## Prerequisites

- AWS CLI v2 installed and configured
- Docker installed and running
- jq installed (for JSON parsing)

---

## Phase 1: VPC and Networking

### 1.1 Create VPC

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=genapp-dev-vpc}]' \
  --query 'Vpc.VpcId' --output text)

# Enable DNS hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

echo "VPC ID: $VPC_ID"
```

### 1.2 Create Subnets

```bash
# Public Subnet 1
PUB_SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=genapp-dev-public-1}]' \
  --query 'Subnet.SubnetId' --output text)

# Public Subnet 2
PUB_SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=genapp-dev-public-2}]' \
  --query 'Subnet.SubnetId' --output text)

# Private Subnet 1
PRV_SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.3.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=genapp-dev-private-1}]' \
  --query 'Subnet.SubnetId' --output text)

# Private Subnet 2
PRV_SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.4.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=genapp-dev-private-2}]' \
  --query 'Subnet.SubnetId' --output text)

echo "Subnets created: $PUB_SUBNET_1, $PUB_SUBNET_2, $PRV_SUBNET_1, $PRV_SUBNET_2"
```

### 1.3 Create Internet Gateway

```bash
# Create IGW
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=genapp-dev-igw}]' \
  --query 'InternetGateway.InternetGatewayId' --output text)

# Attach to VPC
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

echo "IGW ID: $IGW_ID"
```

### 1.4 Create NAT Gateway

```bash
# Allocate Elastic IP
EIP_ALLOC=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)

# Create NAT Gateway
NAT_ID=$(aws ec2 create-nat-gateway \
  --subnet-id $PUB_SUBNET_1 \
  --allocation-id $EIP_ALLOC \
  --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=genapp-dev-nat}]' \
  --query 'NatGateway.NatGatewayId' --output text)

echo "Waiting for NAT Gateway..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_ID
echo "NAT Gateway ID: $NAT_ID"
```

### 1.5 Create required Route Tables

```bash
# Public Route Table
PUB_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=genapp-dev-public-rt}]' \
  --query 'RouteTable.RouteTableId' --output text)

aws ec2 create-route --route-table-id $PUB_RT --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_SUBNET_1
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_SUBNET_2

# Private Route Table
PRV_RT=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=genapp-dev-private-rt}]' \
  --query 'RouteTable.RouteTableId' --output text)

aws ec2 create-route --route-table-id $PRV_RT --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_ID
aws ec2 associate-route-table --route-table-id $PRV_RT --subnet-id $PRV_SUBNET_1
aws ec2 associate-route-table --route-table-id $PRV_RT --subnet-id $PRV_SUBNET_2

echo "Route tables configured"
```

---

## Phase 2: Required Security Groups

```bash
# ALB Security Group
ALB_SG=$(aws ec2 create-security-group \
  --group-name genapp-dev-alb-sg \
  --description "ALB Security Group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress --group-id $ALB_SG --protocol tcp --port 80 --cidr 0.0.0.0/0

# ECS Security Group
ECS_SG=$(aws ec2 create-security-group \
  --group-name genapp-dev-ecs-sg \
  --description "ECS Security Group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress --group-id $ECS_SG --protocol tcp --port 8000 --source-group $ALB_SG
aws ec2 authorize-security-group-ingress --group-id $ECS_SG --protocol tcp --port 8501 --source-group $ALB_SG

echo "Security Groups: ALB=$ALB_SG, ECS=$ECS_SG"
```

---

## Phase 3: Required IAM Roles

### 3.1 ECS Execution Role

```bash
# Create trust policy
cat > /tmp/ecs-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

EXEC_ROLE_ARN=$(aws iam create-role \
  --role-name genapp-dev-execution-role \
  --assume-role-policy-document file:///tmp/ecs-trust.json \
  --query 'Role.Arn' --output text)

aws iam attach-role-policy --role-name genapp-dev-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### 3.2 ECS Task Role

```bash
TASK_ROLE_ARN=$(aws iam create-role \
  --role-name genapp-dev-task-role \
  --assume-role-policy-document file:///tmp/ecs-trust.json \
  --query 'Role.Arn' --output text)

# Attach policies
aws iam attach-role-policy --role-name genapp-dev-task-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name genapp-dev-task-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name genapp-dev-task-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
aws iam attach-role-policy --role-name genapp-dev-task-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonCognitoPowerUser

echo "Roles created: $EXEC_ROLE_ARN, $TASK_ROLE_ARN"
```

---

## Phase 4: Cognito

```bash
# Create User Pool
POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name genapp-dev-users \
  --policies 'PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=false}' \
  --auto-verified-attributes email \
  --query 'UserPool.Id' --output text)

# Create App Client
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $POOL_ID \
  --client-name genapp-dev-client \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --query 'UserPoolClient.ClientId' --output text)

# Create test user
aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username testuser \
  --temporary-password TempPass123!

aws cognito-idp admin-set-user-password \
  --user-pool-id $POOL_ID \
  --username testuser \
  --password TestPass123! \
  --permanent

echo "Cognito Pool: $POOL_ID, Client: $CLIENT_ID"
```

---

## Phase 5: DynamoDB

```bash
aws dynamodb create-table \
  --table-name genapp-dev-chat-history \
  --attribute-definitions \
    AttributeName=session_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=N \
  --key-schema \
    AttributeName=session_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

echo "DynamoDB table created"
```

---

## Phase 6: S3 Bucket

```bash
BUCKET_NAME="genapp-dev-docs-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region us-east-1

aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "S3 Bucket: $BUCKET_NAME"
```

---

## Phase 7: ECR Repositories

```bash
# Create repos
aws ecr create-repository --repository-name genapp-dev-backend
aws ecr create-repository --repository-name genapp-dev-frontend

# Get login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
```

---

## Phase 8: ECS Cluster and Services

### 8.1 Create Cluster

```bash
aws ecs create-cluster --cluster-name genapp-dev-cluster
```

### 8.2 Create ALB

```bash
# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name genapp-dev-alb \
  --subnets $PUB_SUBNET_1 $PUB_SUBNET_2 \
  --security-groups $ALB_SG \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Create target groups
BE_TG=$(aws elbv2 create-target-group \
  --name genapp-dev-be-tg \
  --protocol HTTP --port 8000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path "/" \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

FE_TG=$(aws elbv2 create-target-group \
  --name genapp-dev-fe-tg \
  --protocol HTTP --port 8501 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path "/_stcore/health" \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Create listener with rules
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn=$FE_TG \
  --query 'Listeners[0].ListenerArn' --output text)

# Add /api/* rule
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 10 \
  --conditions Field=path-pattern,Values='/api/*' \
  --actions Type=forward,TargetGroupArn=$BE_TG
```

### 8.3 Register Task Definitions

```bash
# Backend task definition (save as backend-task.json)
cat > /tmp/backend-task.json << EOF
{
  "family": "genapp-dev-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "$EXEC_ROLE_ARN",
  "taskRoleArn": "$TASK_ROLE_ARN",
  "containerDefinitions": [{
    "name": "backend",
    "image": "$(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/genapp-dev-backend:latest",
    "portMappings": [{"containerPort": 8000}],
    "environment": [
      {"name": "AWS_REGION", "value": "us-east-1"},
      {"name": "DYNAMODB_TABLE", "value": "genapp-dev-chat-history"},
      {"name": "KB_ID", "value": "<KB_ID>"},
      {"name": "KB_BUCKET_NAME", "value": "$BUCKET_NAME"},
      {"name": "COGNITO_USER_POOL_ID", "value": "$POOL_ID"},
      {"name": "COGNITO_CLIENT_ID", "value": "$CLIENT_ID"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/genapp-dev-backend",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs",
        "awslogs-create-group": "true"
      }
    }
  }]
}
EOF

aws ecs register-task-definition --cli-input-json file:///tmp/backend-task.json
```

### 8.4 Create Services

```bash
# Backend service
aws ecs create-service \
  --cluster genapp-dev-cluster \
  --service-name genapp-dev-backend \
  --task-definition genapp-dev-backend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$PRV_SUBNET_1,$PRV_SUBNET_2],securityGroups=[$ECS_SG],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=$BE_TG,containerName=backend,containerPort=8000"
```

---

## Phase 9: Knowledge Base

> **Note:** OpenSearch Serverless and Bedrock Knowledge Base creation via CLI is complex. 
> Recommend using Terraform or AWS Console for these components.

```bash
# Check available models
aws bedrock list-foundation-models --query 'modelSummaries[?modelId==`amazon.titan-embed-text-v2:0`]'

# Create KB via boto3 (Python) or use Console
```

---

## Useful Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster genapp-dev-cluster --services genapp-dev-backend genapp-dev-frontend

# View logs
aws logs tail /ecs/genapp-dev-backend --since 10m --follow

# Force deployment
aws ecs update-service --cluster genapp-dev-cluster --service genapp-dev-backend --force-new-deployment

# Test JWT auth
curl -X POST http://<ALB_DNS>/api/chat -H "Content-Type: application/json" -d '{"query":"hello","session_id":"test"}'
# Should return: {"detail":"Missing authorization token"}
```
