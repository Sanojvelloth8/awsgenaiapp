import os
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from tools.kb_tools import retrieve_from_kb, save_section

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
OPUS       = "us.anthropic.claude-opus-4-6-20260213-v1:0"
SONNET     = "us.anthropic.claude-sonnet-4-6-20260217-v1:0"

opus   = BedrockModel(model_id=OPUS,   region_name=AWS_REGION)
sonnet = BedrockModel(model_id=SONNET, region_name=AWS_REGION)

_overview_agent = Agent(
    model=sonnet,
    system_prompt="""You are a senior solutions architect.

Write a SOLUTION OVERVIEW section covering:

## Executive Summary
2-3 paragraphs summarising the solution.

## Solution Approach
How the problem is solved at a high level.

## Key Design Principles
Bullet points of guiding principles (e.g. security-first, cloud-native).

## Technology Stack Summary
| Layer       | Technology | Rationale |
|-------------|------------|-----------|
| Frontend    | ...        | ...       |
| Backend     | ...        | ...       |
| Data        | ...        | ...       |
| Infrastructure | ...     | ...       |

Be concise but complete. Business stakeholders should understand this.""",
    tools=[retrieve_from_kb],
)

_hld_agent = Agent(
    model=opus,
    system_prompt="""You are a principal AWS solutions architect.

Generate a HIGH LEVEL DESIGN (HLD) document covering:

## System Context
Describe the system boundary, external actors, and integrations.

## Architecture Overview
Describe the overall architecture pattern (e.g. microservices, event-driven).

## Component Architecture
For each major component:
- **Component Name**
  - Purpose and responsibilities
  - Technology / AWS service
  - Interfaces (APIs, events, queues)
  - Scaling approach

## Data Flow
Describe the key data flows through the system with numbered steps.

## Security Architecture
- Authentication and authorisation approach
- Network security (VPC, subnets, security groups)
- Data protection (encryption at rest, in transit)
- IAM and least privilege

## Infrastructure Overview
- AWS services used and why
- Multi-AZ / multi-region strategy
- Cost considerations

Be thorough. This document is reviewed by architects and senior engineers.""",
    tools=[retrieve_from_kb],
)

_components_agent = Agent(
    model=sonnet,
    system_prompt="""You are a solutions architect documenting solution components.

For each component in the solution, document:

## Component: [Name]

| Attribute       | Value |
|-----------------|-------|
| Type            | Service / Function / DB / Queue |
| AWS Service     | e.g. ECS Fargate, DynamoDB |
| Purpose         | What it does |
| Inputs          | What it receives |
| Outputs         | What it produces |
| Scaling         | How it scales |
| Failure mode    | What happens if it fails |
| Cost estimate   | Rough monthly cost |

Include ALL components — compute, storage, networking, security, monitoring.""",
    tools=[retrieve_from_kb],
)


@tool
def generate_solution_overview(context: str, session_id: str) -> str:
    """Generate the solution overview with executive summary, approach,
    design principles and technology stack."""
    result = str(_overview_agent(
        f"Project context:\n{context}\n\nGenerate the solution overview."
    ))
    save_section("solution_overview", result, session_id)
    return result


@tool
def generate_hld(context: str, session_id: str) -> str:
    """Generate the High Level Design covering system context, component
    architecture, data flows, security and infrastructure."""
    result = str(_hld_agent(
        f"Project context:\n{context}\n\nGenerate the High Level Design."
    ))
    save_section("hld", result, session_id)
    return result


@tool
def document_solution_components(context: str, session_id: str) -> str:
    """Document all solution components with purpose, AWS service mapping,
    interfaces, scaling and failure modes."""
    result = str(_components_agent(
        f"Project context:\n{context}\n\nDocument all solution components."
    ))
    save_section("solution_components", result, session_id)
    return result
