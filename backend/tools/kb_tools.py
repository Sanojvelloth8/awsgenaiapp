import os
import time
import boto3
import logging
from strands import tool
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
KB_ID          = os.environ.get("KB_ID")
KB_BUCKET_NAME = os.environ.get("KB_BUCKET_NAME")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")

s3                    = boto3.client("s3", region_name=AWS_REGION)
dynamodb              = boto3.resource("dynamodb", region_name=AWS_REGION)
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
bedrock_agent         = boto3.client("bedrock-agent", region_name=AWS_REGION)

RELEVANCE_THRESHOLD = 0.3

@tool
def retrieve_from_kb(query: str) -> str:
    """Search the architecture knowledge base for relevant documents,
    templates, and context. Use this before generating any section."""
    if not KB_ID:
        return "Knowledge base not configured."
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": 5}
            }
        )
        results = response.get("retrievalResults", [])
        chunks = [
            r["content"]["text"]
            for r in results
            if r.get("score", 0) >= RELEVANCE_THRESHOLD
        ]
        if not chunks:
            return "No relevant context found in knowledge base."
        return "\n\n---\n\n".join(chunks)
    except Exception as e:
        logger.error(f"KB retrieval error: {e}")
        return f"KB retrieval failed: {str(e)}"


@tool
def save_section(section_name: str, content: str, session_id: str) -> str:
    """Save a completed document section to S3 for later assembly.
    Call this after generating each section."""
    if not KB_BUCKET_NAME:
        return "S3 bucket not configured."
    try:
        key = f"outputs/{session_id}/{section_name}.md"
        s3.put_object(
            Bucket=KB_BUCKET_NAME,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="text/markdown"
        )
        return f"Section '{section_name}' saved successfully."
    except Exception as e:
        logger.error(f"Save section error: {e}")
        return f"Failed to save section: {str(e)}"


@tool
def get_project_context(session_id: str) -> str:
    """Retrieve the full conversation and project context for this session
    from DynamoDB history."""
    if not DYNAMODB_TABLE:
        return "No conversation history available."
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.query(
            KeyConditionExpression=Key("session_id").eq(session_id),
            ScanIndexForward=False,
            Limit=20
        )
        items = response.get("Items", [])
        items.reverse()
        if not items:
            return "No prior conversation history."
        lines = []
        for item in items:
            role = item.get("role", "")
            content = item.get("content", "")
            lines.append(f"{role.capitalize()}: {content}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Get history error: {e}")
        return f"Failed to retrieve history: {str(e)}"


@tool
def sync_knowledge_base() -> str:
    """Trigger re-indexing of the knowledge base after new documents
    are uploaded to S3."""
    if not KB_ID:
        return "KB not configured."
    try:
        ds = bedrock_agent.list_data_sources(
            knowledgeBaseId=KB_ID, maxResults=1
        )
        summaries = ds.get("dataSourceSummaries", [])
        if not summaries:
            return "No data source found."
        job = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=summaries[0]["dataSourceId"]
        )
        job_id = job["ingestionJob"]["ingestionJobId"]
        return f"KB sync started. Job ID: {job_id}"
    except Exception as e:
        logger.error(f"Sync KB error: {e}")
        return f"KB sync failed: {str(e)}"


@tool
def load_all_sections(session_id: str) -> str:
    """Load all previously saved document sections from S3 for assembly."""
    if not KB_BUCKET_NAME:
        return "S3 bucket not configured."
    try:
        prefix = f"outputs/{session_id}/"
        response = s3.list_objects_v2(Bucket=KB_BUCKET_NAME, Prefix=prefix)
        objects = response.get("Contents", [])
        if not objects:
            return "No sections found for this session."

        SECTION_ORDER = [
            "executive_summary", "business_requirements",
            "functional_requirements", "nonfunctional_requirements",
            "scope", "assumptions", "risks_dependencies",
            "adrs", "solution_overview", "hld",
            "solution_components", "lld", "node_flow",
            "detailed_design", "diagrams"
        ]

        sections = {}
        for obj in objects:
            key = obj["Key"]
            name = key.replace(prefix, "").replace(".md", "")
            body = s3.get_object(Bucket=KB_BUCKET_NAME, Key=key)
            sections[name] = body["Body"].read().decode("utf-8")

        ordered = []
        for name in SECTION_ORDER:
            if name in sections:
                ordered.append(f"## {name.replace('_', ' ').title()}\n\n{sections[name]}")
        for name, content in sections.items():
            if name not in SECTION_ORDER:
                ordered.append(f"## {name.replace('_', ' ').title()}\n\n{content}")

        return "\n\n---\n\n".join(ordered)
    except Exception as e:
        logger.error(f"Load sections error: {e}")
        return f"Failed to load sections: {str(e)}"
