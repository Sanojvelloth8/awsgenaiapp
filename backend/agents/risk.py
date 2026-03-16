import os
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from tools.kb_tools import retrieve_from_kb, save_section

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
OPUS       = "us.anthropic.claude-opus-4-6-20260213-v1:0"
SONNET     = "us.anthropic.claude-sonnet-4-6-20260217-v1:0"

opus   = BedrockModel(model_id=OPUS,   region_name=AWS_REGION)
sonnet = BedrockModel(model_id=SONNET, region_name=AWS_REGION)

_risk_agent = Agent(
    model=sonnet,
    system_prompt="""You are a risk management specialist for cloud and software projects.

Identify and document risks and dependencies.

### Risk Register
| ID  | Risk Description | Category | Probability | Impact | Score | Mitigation Strategy | Owner |
|-----|-----------------|----------|-------------|--------|-------|---------------------|-------|
| R01 | ...             | Technical| H           | H      | 9     | ...                 | Arch  |

Categories: Technical, Business, Security, Delivery, Operational
Probability/Impact: H=3, M=2, L=1. Score = P x I.
Sort by score descending. Include top 10 risks minimum.""",
    tools=[retrieve_from_kb],
)

_adr_agent = Agent(
    model=opus,
    system_prompt="""You are an architecture decision specialist.

Generate Architecture Decision Records (ADRs) for key design decisions.

For each ADR use this format:

## ADR-001: [Decision Title]

**Status:** Proposed | Accepted | Deprecated

**Context:**
What is the situation that requires a decision?

**Decision:**
What was decided?

**Rationale:**
Why was this chosen over alternatives?

**Alternatives Considered:**
1. Alternative A — pros/cons
2. Alternative B — pros/cons

**Consequences:**
- Positive consequences
- Negative consequences / trade-offs

**Review Date:** [when to revisit]

---

Generate ADRs for all significant architectural decisions in the project.
Minimum 5 ADRs for a well-designed system.""",
    tools=[retrieve_from_kb],
)


@tool
def identify_risks_and_dependencies(context: str, session_id: str) -> str:
    """Identify technical, business and delivery risks with probability,
    impact scores and mitigation strategies."""
    result = str(_risk_agent(
        f"Project context:\n{context}\n\nGenerate the risk register."
    ))
    save_section("risks_dependencies", result, session_id)
    return result


@tool
def generate_adrs(context: str, session_id: str) -> str:
    """Generate Architecture Decision Records (ADRs) for all key
    design decisions with context, rationale and alternatives considered."""
    result = str(_adr_agent(
        f"Project context:\n{context}\n\n"
        f"Generate comprehensive ADRs for all key architecture decisions."
    ))
    save_section("adrs", result, session_id)
    return result
