import os
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from tools.kb_tools import retrieve_from_kb, save_section

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SONNET     = "us.anthropic.claude-sonnet-4-6-20260217-v1:0"

sonnet = BedrockModel(model_id=SONNET, region_name=AWS_REGION)

_lld_agent = Agent(
    model=sonnet,
    system_prompt="""You are a senior software architect writing
Low Level Design (LLD) documentation.

For each component generate:

## [Component Name] — Low Level Design

### API / Interface Contracts
Document all endpoints, events or messages:
| Method | Path / Topic | Request Body | Response | Auth |
|--------|-------------|--------------|----------|------|

### Data Models
```
ClassName / TableName {
  field: type  // description
}
```

### Sequence Diagrams (text format)
Describe key flows step by step:
1. Client → Service: action
2. Service → DB: query
3. DB → Service: result
4. Service → Client: response

### Business Logic
Key algorithms, validations, rules.

### Error Handling
| Error Condition | HTTP Code | Response | Recovery |
|----------------|-----------|----------|----------|

### Configuration
Environment variables and their purpose.""",
    tools=[retrieve_from_kb],
)

_nodeflow_agent = Agent(
    model=sonnet,
    system_prompt="""You are a solutions architect documenting node flows
and request processing pipelines.

Document the NODE FLOW for each key user journey:

## Flow: [Flow Name]

**Trigger:** What initiates this flow

**Happy Path:**
```
[Node 1: Description]
    |
    ↓ condition / data passed
[Node 2: Description]
    |
    ↓
[Node 3: Description]
    ...
    ↓
[End: Result]
```

**Error Paths:**
Document what happens at each failure point.

**Timing:**
Approximate latency at each step.

Cover: user authentication flow, document upload flow,
agent generation flow, document download flow.""",
    tools=[retrieve_from_kb],
)

_diagram_agent = Agent(
    model=sonnet,
    system_prompt="""You are an architecture diagram specialist.

Generate architecture diagrams as Mermaid syntax.

For each diagram provide:
1. A brief description of what the diagram shows
2. The Mermaid code block

Required diagrams:

### System Context Diagram
```mermaid
graph TB
  ...
```

### Component Architecture Diagram
```mermaid
graph LR
  ...
```

### Sequence Diagram — Key Flow
```mermaid
sequenceDiagram
  ...
```

### Infrastructure Diagram
```mermaid
graph TB
  subgraph AWS
    ...
  end
```

Use clear, descriptive node labels.
Streamlit renders Mermaid natively so these will display as visual diagrams.""",
    tools=[retrieve_from_kb],
)


@tool
def generate_lld(context: str, session_id: str) -> str:
    """Generate Low Level Design for each component including API contracts,
    data models, sequence diagrams and error handling."""
    result = str(_lld_agent(
        f"Project context:\n{context}\n\nGenerate detailed Low Level Design."
    ))
    save_section("lld", result, session_id)
    return result


@tool
def generate_node_flow(context: str, session_id: str) -> str:
    """Generate node flow diagrams for all key user journeys
    showing step-by-step processing with error paths."""
    result = str(_nodeflow_agent(
        f"Project context:\n{context}\n\nGenerate node flows for all key journeys."
    ))
    save_section("node_flow", result, session_id)
    return result


@tool
def generate_diagrams(context: str, session_id: str) -> str:
    """Generate architecture diagrams as Mermaid syntax:
    system context, component, sequence and infrastructure diagrams."""
    result = str(_diagram_agent(
        f"Project context:\n{context}\n\nGenerate all architecture diagrams."
    ))
    save_section("diagrams", result, session_id)
    return result
