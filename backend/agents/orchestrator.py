import os
from strands import Agent
from strands.models.bedrock import BedrockModel

from agents.requirements import (
    collect_functional_requirements,
    collect_nonfunctional_requirements,
    collect_business_requirements,
)
from agents.scope import define_scope_and_assumptions
from agents.risk import identify_risks_and_dependencies, generate_adrs
from agents.solution import (
    generate_solution_overview,
    generate_hld,
    document_solution_components,
)
from agents.detailed import generate_lld, generate_node_flow, generate_diagrams
from agents.assembler import assemble_final_document
from tools.kb_tools import retrieve_from_kb, get_project_context

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
OPUS       = "us.anthropic.claude-opus-4-6-20260213-v1:0"

opus = BedrockModel(model_id=OPUS, region_name=AWS_REGION)

ORCHESTRATOR_PROMPT = """You are a principal solutions architect orchestrating
the generation of a complete, professional solution design document.

You have access to specialist agents for each document section.
Each specialist agent knows exactly what to generate for their section.

## Your behaviour

**For a FULL solution design document**, call ALL agents in this order:
1. get_project_context — retrieve prior conversation context
2. retrieve_from_kb — get relevant templates and examples
3. collect_business_requirements
4. collect_functional_requirements
5. collect_nonfunctional_requirements
6. define_scope_and_assumptions
7. identify_risks_and_dependencies
8. generate_adrs
9. generate_solution_overview
10. generate_hld
11. document_solution_components
12. generate_lld
13. generate_node_flow
14. generate_diagrams
15. assemble_final_document — ALWAYS call last

**For PARTIAL requests**, call only the relevant agents:
- "give me the HLD" → retrieve_from_kb, generate_hld only
- "what are the risks" → retrieve_from_kb, identify_risks_and_dependencies only
- "generate ADRs" → retrieve_from_kb, generate_adrs only
- "just requirements" → all three requirements agents

**Always:**
- First call retrieve_from_kb with a relevant query to get context
- Pass the user's full request + retrieved context to each specialist
- Pass the session_id to every agent call
- Call assemble_final_document at the end for full doc requests

**Never:**
- Generate content yourself — always delegate to specialist agents
- Skip retrieve_from_kb — context improves every agent's output
- Call assemble_final_document before other agents have run
"""

def get_orchestrator() -> Agent:
    """Return a fresh orchestrator agent instance."""
    return Agent(
        model=opus,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            retrieve_from_kb,
            get_project_context,
            collect_business_requirements,
            collect_functional_requirements,
            collect_nonfunctional_requirements,
            define_scope_and_assumptions,
            identify_risks_and_dependencies,
            generate_adrs,
            generate_solution_overview,
            generate_hld,
            document_solution_components,
            generate_lld,
            generate_node_flow,
            generate_diagrams,
            assemble_final_document,
        ],
    )
