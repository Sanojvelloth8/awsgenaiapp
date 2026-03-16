import os
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from tools.kb_tools import retrieve_from_kb, save_section

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SONNET     = "us.anthropic.claude-sonnet-4-6-20260217-v1:0"

sonnet = BedrockModel(model_id=SONNET, region_name=AWS_REGION)

_scope_agent = Agent(
    model=sonnet,
    system_prompt="""You are a project scoping specialist.

Define clearly what IS and IS NOT in scope for this project.

Structure your output as:

### In Scope
- List each item clearly

### Out of Scope
- List each explicitly excluded item
- Include brief rationale for exclusion

### Key Assumptions
| # | Assumption | Impact if Wrong |
|---|------------|-----------------|
| 1 | ...        | ...             |

### Dependencies
| Dependency | Owner | Required By | Risk if Delayed |
|------------|-------|-------------|-----------------|

Be specific. Vague scope leads to project failure.""",
    tools=[retrieve_from_kb],
)


@tool
def define_scope_and_assumptions(context: str, session_id: str) -> str:
    """Define in-scope items, out-of-scope items, key assumptions,
    and project dependencies."""
    result = str(_scope_agent(
        f"Project context:\n{context}\n\nDefine scope, assumptions and dependencies."
    ))
    save_section("scope", result, session_id)
    return result
