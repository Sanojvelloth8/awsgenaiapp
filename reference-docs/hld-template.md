# High Level Design (HLD) Template

## 1. Executive Summary
[2-3 paragraphs summarising the solution, business problem solved, and key outcomes]

## 2. System Context

### 2.1 System Boundary
[Describe what is inside and outside the system boundary]

### 2.2 External Actors
| Actor | Type | Interaction |
|-------|------|-------------|
| End User | Human | Uses web UI |
| Admin | Human | Manages system |
| External API | System | Provides data |

### 2.3 Integration Points
[List all external systems this solution integrates with]

## 3. Architecture Overview

### 3.1 Architecture Pattern
[Describe the pattern: microservices / event-driven / serverless / monolith]

### 3.2 Key Design Principles
- Security-first: all data encrypted, least-privilege access
- Cloud-native: leverage managed services over self-managed
- Scalability: stateless services, horizontal scaling
- Observability: logging, metrics, tracing built-in
- Cost optimisation: right-size resources, scale to zero where possible

## 4. Component Architecture

### 4.1 Presentation Layer
**Component:** [Name]
- Purpose: [What it does]
- Technology: [Framework/Service]
- Hosting: [ECS/Lambda/S3]
- Scaling: [How it scales]

### 4.2 Application Layer
**Component:** [Name]
- Purpose: [What it does]
- Technology: [Framework/Service]
- Key endpoints: [API routes]
- Scaling: [How it scales]

### 4.3 Data Layer
**Component:** [Name]
- Purpose: [What it stores]
- Technology: [Database/Service]
- Data model: [Key entities]
- Backup/Recovery: [Strategy]

## 5. Data Flow

### 5.1 Primary Flow: [Flow Name]
1. User submits request via [channel]
2. [Component A] validates and authenticates
3. [Component B] processes the request
4. [Component C] retrieves/stores data
5. Response returned to user

## 6. Security Architecture

### 6.1 Authentication & Authorisation
- AuthN: [Mechanism — Cognito/OAuth/SAML]
- AuthZ: [Mechanism — RBAC/ABAC/IAM]
- Token: [JWT/SAML/session]

### 6.2 Network Security
- VPC with public/private subnet separation
- ALB in public subnet, workloads in private
- Security groups with least-privilege rules
- No direct internet access from private subnets

### 6.3 Data Protection
- Encryption at rest: AES-256 (AWS managed keys)
- Encryption in transit: TLS 1.2+
- Secrets management: AWS Secrets Manager / Parameter Store

## 7. Infrastructure Overview

### 7.1 AWS Services Used
| Service | Purpose | Justification |
|---------|---------|---------------|
| ECS Fargate | Container hosting | Serverless, no EC2 management |
| RDS/DynamoDB | Data storage | Managed, scalable |
| S3 | Object storage | Durable, cheap |
| CloudFront | CDN | Global performance |

### 7.2 Multi-AZ Strategy
[Describe availability zone deployment strategy]

### 7.3 Cost Estimate
| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| ECS | $X | 2 tasks, 0.25 vCPU |
| ALB | $X | Fixed + LCU |
| Total | $X | Dev environment |

## 8. Non-Functional Characteristics
- Availability: 99.9% uptime target
- Latency: P95 < 2s for API responses
- Scalability: 0-100 concurrent users
- RPO: 24 hours | RTO: 4 hours
