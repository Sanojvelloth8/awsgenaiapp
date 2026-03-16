import os
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from tools.kb_tools import retrieve_from_kb, save_section

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SONNET     = "us.anthropic.claude-sonnet-4-6-20260217-v1:0"

sonnet = BedrockModel(model_id=SONNET, region_name=AWS_REGION)

# ── Functional Requirements Agent ─────────────────────────────────────────
_fr_agent = Agent(
    model=sonnet,
    system_prompt="""You are a senior business analyst specialising in
functional requirements for software and cloud architecture projects.

Given project context, extract and document FUNCTIONAL REQUIREMENTS only.

Format each requirement as:
| ID     | Description | Priority (H/M/L) | Acceptance Criteria |
|--------|-------------|------------------|---------------------|
| FR-001 | ...         | H                | ...                 |

Group by: User-Facing Features, System Behaviours, Integrations, Data Management.
Be specific and testable. Do not include non-functional concerns.""",
    tools=[retrieve_from_kb],
)

# ── Non-Functional Requirements Agent ─────────────────────────────────────
_nfr_agent = Agent(
    model=sonnet,
    system_prompt="""You are a solutions architect specialising in
non-functional requirements for cloud systems.

Given project context, document NON-FUNCTIONAL REQUIREMENTS covering:
- Performance (latency, throughput, response times)
- Scalability (load expectations, growth projections)
- Availability (uptime SLA, RTO, RPO)
- Security (auth, encryption, compliance)
- Observability (logging, monitoring, alerting)
- Maintainability (deployability, testability)

Format as a table with: ID | Category | Requirement | Metric | Priority""",
    tools=[retrieve_from_kb],
)

# ── Business Requirements Agent ────────────────────────────────────────────
_br_agent = Agent(
    model=sonnet,
    system_prompt="""You are a business analyst specialising in
business requirements and stakeholder alignment.

Given project context, document BUSINESS REQUIREMENTS covering:
- Business Goals and Objectives
- Key Performance Indicators (KPIs)
- Stakeholders and their concerns
- Business Constraints
- Success Criteria
- Business Value / ROI justification

Use structured headings. Be concise and business-focused, not technical.""",
    tools=[retrieve_from_kb],
)


# ── Tool wrappers exposed to orchestrator ─────────────────────────────────
@tool
def collect_functional_requirements(context: str, session_id: str) -> str:
    """Collect and document all functional requirements from the project
    context. Returns a formatted requirements table."""
    result = str(_fr_agent(
        f"Project context:\n{context}\n\nGenerate the functional requirements."
    ))
    save_section("functional_requirements", result, session_id)
    return result


@tool
def collect_nonfunctional_requirements(context: str, session_id: str) -> str:
    """Collect and document all non-functional requirements: performance,
    scalability, availability, security, observability."""
    result = str(_nfr_agent(
        f"Project context:\n{context}\n\nGenerate the non-functional requirements."
    ))
    save_section("nonfunctional_requirements", result, session_id)
    return result


@tool
def collect_business_requirements(context: str, session_id: str) -> str:
    """Collect and document business goals, KPIs, stakeholders,
    constraints and success criteria."""
    result = str(_br_agent(
        f"Project context:\n{context}\n\nGenerate the business requirements."
    ))
    save_section("business_requirements", result, session_id)
    return result
