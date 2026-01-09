# GenApp RAG Application - Design Document

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [High-Level Design (HLD)](#high-level-design-hld)
3. [Low-Level Design (LLD)](#low-level-design-lld)
4. [Solution Components](#solution-components)
5. [Architecture Decisions](#architecture-decisions)
6. [Data Flow](#data-flow)
7. [Security Architecture](#security-architecture)
8. [Implementation Guide](#implementation-guide)

---

## Executive Summary.

GenApp is a **Retrieval-Augmented Generation (RAG)** application that enables users to upload documents and ask questions about them using natural language. The system combines AWS Bedrock's Knowledge Base for semantic document retrieval with Amazon Titan for intelligent response generation.

### Key Capabilities

- 📄 Document upload and indexing
- 🔍 Semantic search across documents
- 💬 Conversational AI with memory
- 🔐 JWT-based authentication
- 📊 Hybrid RAG (documents + general knowledge)

---

## High Level Design (HLD)

### System Overview.

```mermaid
graph TB
    subgraph "Users"
        U[End Users]
    end
    
    subgraph "Presentation Layer"
        ALB[Application Load Balancer]
        FE[Streamlit Frontend]
    end
    
    subgraph "Application Layer"
        BE[FastAPI Backend]
    end
    
    subgraph "AI/ML Layer"
        KB[Bedrock Knowledge Base]
        TITAN[Amazon Titan LLM]
        EMB[Titan Embeddings]
    end
    
    subgraph "Data Layer"
        S3[S3 - Documents]
        DDB[DynamoDB - Chat History]
        OS[OpenSearch Serverless]
    end
    
    subgraph "Security Layer"
        COG[Cognito User Pool]
    end
    
    U --> ALB
    ALB --> FE
    FE --> BE
    BE --> KB
    BE --> TITAN
    KB --> EMB
    KB --> S3
    KB --> OS
    BE --> DDB
    FE --> COG
    BE --> COG
```

### Component Summary

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Presentation** | Streamlit | User interface |
| **API** | FastAPI | REST API, business logic |
| **AI/ML** | Bedrock KB + Titan | RAG + LLM |
| **Storage** | S3, DynamoDB, OpenSearch | Documents, history, vectors |
| **Security** | Cognito | Authentication & JWT |
| **Infrastructure** | ECS Fargate | Serverless containers |

---

## Low-Level Design (LLD)

### 1. Frontend Component (Streamlit)

```
frontend/
├── app.py              # Main application
├── requirements.txt    # Dependencies
└── Dockerfile          # Container build
```

#### Key Functions

| Function | Purpose |
|----------|---------|
| `login()` | Authenticates with Cognito, stores JWT |
| `get_auth_headers()` | Returns Authorization header with JWT |
| `upload_file()` | Gets presigned URL, uploads to S3 |
| `send_message()` | Sends query to backend with JWT |

#### Flow Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant COG as Cognito
    participant BE as Backend
    
    U->>FE: Enter credentials
    FE->>COG: InitiateAuth
    COG-->>FE: JWT Token
    FE->>FE: Store token in session
    
    U->>FE: Ask question
    FE->>BE: POST /api/chat + JWT
    BE->>BE: Validate JWT
    BE-->>FE: Response
    FE-->>U: Display answer
```

### 2. Backend Component (FastAPI)

```
backend/
├── main.py             # API endpoints
├── requirements.txt    # Dependencies
└── Dockerfile          # Container build
```

#### API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/` | GET | No | Health check |
| `/api/chat` | POST | JWT | Process query, return answer |
| `/api/history/{session_id}` | GET | JWT | Get chat history |
| `/api/upload-url` | GET | JWT | Get presigned S3 URL |
| `/api/sync` | POST | JWT | Trigger KB ingestion |

#### Chat Endpoint Flow

```mermaid
flowchart TD
    A[Receive Query] --> B[Validate JWT]
    B --> C[Get History from DynamoDB]
    C --> D[Query Knowledge Base]
    D --> E{Relevant Results?}
    E -->|Yes| F[Build RAG Prompt]
    E -->|No| G[Build General Prompt]
    F --> H[Invoke Titan LLM]
    G --> H
    H --> I[Save to DynamoDB]
    I --> J[Return Response]
```

### 3. Knowledge Base Component

```mermaid
graph LR
    subgraph "Ingestion Pipeline"
        S3[S3 Documents] --> CHUNK[Chunking]
        CHUNK --> EMB[Titan Embeddings]
        EMB --> OS[OpenSearch Vectors]
    end
    
    subgraph "Query Pipeline"
        Q[User Query] --> QEMB[Query Embedding]
        QEMB --> SEARCH[Vector Search]
        SEARCH --> OS
        OS --> RESULTS[Ranked Results]
    end
```

#### Configuration

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Embedding Model | `amazon.titan-embed-text-v2:0` | Text to vectors |
| Vector Dimensions | 1024 | Embedding size |
| Chunk Size | 300 tokens | Document splitting |
| Chunk Overlap | 20% | Context continuity |
| Top-K Results | 3 | Retrieved contexts |

### 4. Authentication Component

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant COG as Cognito
    participant BE as Backend
    
    FE->>COG: InitiateAuth(username, password)
    COG-->>FE: IdToken (JWT)
    
    FE->>BE: API Call + Authorization: Bearer <JWT>
    BE->>BE: Decode JWT header, get kid
    BE->>COG: Fetch JWKS (cached)
    COG-->>BE: Public Keys
    BE->>BE: Verify signature + claims
    BE-->>FE: Response (if valid)
```

---

## Solution Components

### AWS Services Used

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **VPC** | Network isolation | 10.0.0.0/16, 2 AZs |
| **ECS Fargate** | Container orchestration | 256 CPU, 512 MB |
| **ALB** | Load balancing | Path-based routing |
| **ECR** | Container registry | 2 repos (FE/BE) |
| **S3** | Document storage | Private, versioned |
| **DynamoDB** | Chat history | On-demand, TTL enabled |
| **OpenSearch Serverless** | Vector store | Managed, auto-scaling |
| **Bedrock Knowledge Base** | RAG retrieval | S3 data source |
| **Bedrock Runtime** | LLM inference | Titan Text Express |
| **Cognito** | Authentication | User pool + app client |

### Resource Specifications

```mermaid
graph TB
    subgraph "Network Layer"
        VPC[VPC: 10.0.0.0/16]
        PUB1[Public: 10.0.1.0/24]
        PUB2[Public: 10.0.2.0/24]
        PRV1[Private: 10.0.3.0/24]
        PRV2[Private: 10.0.4.0/24]
        IGW[Internet Gateway]
        NAT[NAT Gateway]
    end
    
    VPC --> PUB1
    VPC --> PUB2
    VPC --> PRV1
    VPC --> PRV2
    PUB1 --> IGW
    PUB1 --> NAT
    PRV1 --> NAT
```

---

## Architecture Decisions

### ADR-001: ECS Fargate vs EC2

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Choice** | ECS Fargate | Serverless, no EC2 management |
| **Trade-off** | Higher per-task cost | Lower operational overhead |
| **Alternative** | ECS on EC2 | Better for steady-state workloads |

### ADR-002: OpenSearch Serverless vs Provisioned

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Choice** | Serverless | Auto-scaling, no capacity planning |
| **Trade-off** | Higher per-OCU cost | Zero management |
| **Alternative** | Provisioned | Better for predictable workloads |

### ADR-003: Amazon Titan vs Claude

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Choice** | Amazon Titan | Included in Bedrock, no extra setup |
| **Trade-off** | Content filters (e.g., "voting") | Lower cost, simpler integration |
| **Alternative** | Claude 3.5 Sonnet | Better quality, requires payment |

### ADR-004: JWT Validation Location

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Choice** | Backend (FastAPI) | Full control, no API Gateway needed |
| **Trade-off** | Custom code | Flexibility |
| **Alternative** | API Gateway + Authorizer | Managed, but adds latency |

### ADR-005: Conversation Memory

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Choice** | DynamoDB with TTL | Serverless, auto-cleanup |
| **Trade-off** | No complex queries | Simple, scalable |
| **Alternative** | Redis | Faster, but needs management |

---

## Data Flow

### Document Upload Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant S3 as S3
    participant KB as Knowledge Base
    
    U->>FE: Upload file
    FE->>BE: GET /api/upload-url?filename=doc.pdf
    BE->>S3: Generate presigned URL
    S3-->>BE: Presigned PUT URL
    BE-->>FE: {upload_url, filename}
    FE->>S3: PUT file (presigned)
    S3-->>FE: 200 OK
    FE->>BE: POST /api/sync
    BE->>KB: Start ingestion job
    KB->>S3: Read documents
    KB->>KB: Chunk + Embed + Index
    KB-->>BE: Job started
    BE-->>FE: {job_id, status}
```

### Query Processing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant DDB as DynamoDB
    participant KB as Knowledge Base
    participant LLM as Titan LLM
    
    U->>FE: Ask question
    FE->>BE: POST /api/chat
    BE->>DDB: Get conversation history
    DDB-->>BE: Last 6 messages
    BE->>KB: Retrieve(query, k=3)
    KB-->>BE: Relevant chunks + scores
    BE->>BE: Build prompt (history + context + query)
    BE->>LLM: Invoke model
    LLM-->>BE: Generated answer
    BE->>DDB: Save user message
    BE->>DDB: Save assistant message
    BE-->>FE: {answer, sources}
    FE-->>U: Display response
```

---

## Security Architecture

### Network Security

```mermaid
graph TB
    subgraph "Internet"
        USER[Users]
    end
    
    subgraph "Public Subnet"
        ALB[ALB<br/>SG: 80 from 0.0.0.0/0]
        NAT[NAT Gateway]
    end
    
    subgraph "Private Subnet"
        FE[Frontend<br/>SG: 8501 from ALB]
        BE[Backend<br/>SG: 8000 from ALB]
    end
    
    subgraph "AWS Services"
        BEDROCK[Bedrock]
        S3[S3]
        DDB[DynamoDB]
    end
    
    USER --> ALB
    ALB --> FE
    ALB --> BE
    FE --> NAT --> BEDROCK
    BE --> NAT --> S3
    BE --> NAT --> DDB
```

### Authentication Flow

| Step | Component | Action |
|------|-----------|--------|
| 1 | Frontend | User enters credentials |
| 2 | Cognito | Validates password, returns JWT |
| 3 | Frontend | Stores JWT in session |
| 4 | Frontend | Sends JWT with every API call |
| 5 | Backend | Validates JWT signature with JWKS |
| 6 | Backend | Extracts user identity from claims |

### IAM Roles

| Role | Purpose | Key Permissions |
|------|---------|-----------------|
| `genapp-dev-execution-role` | ECS task execution | ECR pull, CloudWatch logs |
| `genapp-dev-task-role` | Application runtime | Bedrock, S3, DynamoDB, Cognito |
| `genapp-dev-kb-role` | Knowledge Base | S3 read, OpenSearch, Bedrock embeddings |

---

## Implementation Guide

### Option 1: Terraform (Recommended)

See [Terraform Implementation Guide](./terraform-implementation-guide.md)

```bash
# Quick start
cd terraform
terraform init
terraform plan
terraform apply -auto-approve
```

### Option 2: AWS CLI

See [AWS CLI Implementation Guide](./aws-cli-implementation-guide.md)

### Option 3: AWS Console (GUI)

See [AWS Console Implementation Guide](./aws-console-implementation-guide.md)

---

## Appendix

### Environment Variables

| Variable | Component | Purpose |
|----------|-----------|---------|
| `AWS_REGION` | Backend | AWS region |
| `KB_ID` | Backend | Knowledge Base ID |
| `KB_BUCKET_NAME` | Backend | S3 bucket for documents |
| `DYNAMODB_TABLE` | Backend | Chat history table |
| `COGNITO_USER_POOL_ID` | Backend | User Pool for JWT validation |
| `COGNITO_CLIENT_ID` | Backend | App Client for JWT validation |
| `COGNITO_USER_POOL_ID` | Frontend | User Pool for login |
| `COGNITO_CLIENT_ID` | Frontend | App Client for login |
| `BACKEND_URL` | Frontend | Backend API URL |

### Cost Estimation (Development)

| Service | Estimated Monthly Cost |
|---------|----------------------|
| ECS Fargate (2 tasks) | ~$30 |
| NAT Gateway | ~$35 |
| OpenSearch Serverless | ~$50 (min 2 OCUs) |
| ALB | ~$20 |
| S3 | ~$1 |
| DynamoDB | ~$1 |
| Bedrock | Pay per token |
| **Total** | **~$137/month** |

### References

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
