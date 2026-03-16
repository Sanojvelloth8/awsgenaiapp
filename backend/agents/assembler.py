import os
import time
import boto3
import logging
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from tools.kb_tools import load_all_sections, save_section

logger = logging.getLogger(__name__)

AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
KB_BUCKET_NAME = os.environ.get("KB_BUCKET_NAME")
HAIKU          = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

haiku = BedrockModel(model_id=HAIKU, region_name=AWS_REGION)
s3    = boto3.client("s3", region_name=AWS_REGION)

_assembler_agent = Agent(
    model=haiku,
    system_prompt="""You are a technical writer assembling a solution
design document from individual sections.

Given all sections, produce a clean, professional final document:

1. Add a proper title page header
2. Add a table of contents with section numbers
3. Ensure consistent heading levels throughout
4. Add page break markers (---) between major sections
5. Fix any formatting inconsistencies
6. Ensure section cross-references are correct

Do NOT change the technical content — only improve structure and formatting.
Output clean Markdown ready for conversion to DOCX or PDF.""",
    tools=[load_all_sections],
)


@tool
def assemble_final_document(session_id: str, project_name: str) -> str:
    """Assemble all generated sections into a single, well-formatted
    solution design document. Call this last after all sections are saved."""
    result = str(_assembler_agent(
        f"Session ID: {session_id}\nProject: {project_name}\n\n"
        f"Load all sections and assemble the final solution design document."
    ))

    # Save final assembled doc
    if KB_BUCKET_NAME:
        try:
            key = f"outputs/{session_id}/FINAL_solution_design.md"
            s3.put_object(
                Bucket=KB_BUCKET_NAME,
                Key=key,
                Body=result.encode("utf-8"),
                ContentType="text/markdown"
            )
        except Exception as e:
            logger.error(f"Failed to save final doc: {e}")

    return result
