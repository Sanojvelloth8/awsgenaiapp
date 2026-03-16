import os
import time
import logging
import httpx
import boto3
from boto3.dynamodb.conditions import Key
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from typing import List, Optional
from jose import jwt, JWTError

from agents.orchestrator import get_orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────
AWS_REGION         = os.environ.get("AWS_REGION", "us-east-1")
KB_BUCKET_NAME     = os.environ.get("KB_BUCKET_NAME")
DYNAMODB_TABLE     = os.environ.get("DYNAMODB_TABLE")
COGNITO_USER_POOL  = os.environ.get("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID  = os.environ.get("COGNITO_CLIENT_ID")
ALLOWED_ORIGINS    = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
HISTORY_LIMIT      = 10

# ── AWS Clients ────────────────────────────────────────────────────────────
s3       = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

# ── JWT / Auth ─────────────────────────────────────────────────────────────
security      = HTTPBearer(auto_error=False)
_jwks_cache   = None
_jwks_expiry  = 0
JWKS_TTL      = 3600

def get_cognito_jwks() -> dict:
    global _jwks_cache, _jwks_expiry
    if _jwks_cache is None or time.time() > _jwks_expiry:
        url = (f"https://cognito-idp.{AWS_REGION}.amazonaws.com"
               f"/{COGNITO_USER_POOL}/.well-known/jwks.json")
        _jwks_cache  = httpx.get(url, timeout=10).json()
        _jwks_expiry = time.time() + JWKS_TTL
    return _jwks_cache

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not COGNITO_USER_POOL or not COGNITO_CLIENT_ID:
        return {"sub": "anonymous"}
    if not credentials:
        raise HTTPException(401, "Missing authorization token")
    token = credentials.credentials
    try:
        jwks     = get_cognito_jwks()
        kid      = jwt.get_unverified_header(token).get("kid")
        rsa_key  = next(
            (k for k in jwks.get("keys", []) if k.get("kid") == kid), None
        )
        if not rsa_key:
            raise HTTPException(401, "Invalid token: key not found")
        payload = jwt.decode(
            token, rsa_key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=(f"https://cognito-idp.{AWS_REGION}.amazonaws.com"
                    f"/{COGNITO_USER_POOL}"),
        )
        return payload
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {e}")
    except Exception as e:
        raise HTTPException(401, f"Token validation failed: {e}")

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="GenApp Architecture Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ─────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str
    session_id: str

    @field_validator("query")
    @classmethod
    def query_length(cls, v: str) -> str:
        if len(v.strip()) == 0:
            raise ValueError("Query cannot be empty")
        if len(v) > 4000:
            raise ValueError("Query too long (max 4000 chars)")
        return v

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    download_url: Optional[str] = None

# ── DynamoDB helpers ───────────────────────────────────────────────────────
def get_history(session_id: str, limit: int = HISTORY_LIMIT) -> str:
    if not DYNAMODB_TABLE:
        return ""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        items = table.query(
            KeyConditionExpression=Key("session_id").eq(session_id),
            ScanIndexForward=False,
            Limit=limit,
        ).get("Items", [])
        items.reverse()
        return "\n".join(
            f"{i['role'].capitalize()}: {i['content']}" for i in items
        )
    except Exception as e:
        logger.warning(f"get_history failed: {e}")
        return ""

def save_history(session_id: str, user_msg: str, assistant_msg: str) -> None:
    if not DYNAMODB_TABLE:
        return
    try:
        table   = dynamodb.Table(DYNAMODB_TABLE)
        ts      = int(time.time() * 1000)
        ttl_val = int(time.time()) + 604800  # 7 days
        with table.batch_writer() as batch:
            batch.put_item(Item={
                "session_id": session_id, "timestamp": ts,
                "role": "user", "content": user_msg, "ttl": ttl_val,
            })
            batch.put_item(Item={
                "session_id": session_id, "timestamp": ts + 1,
                "role": "assistant", "content": assistant_msg, "ttl": ttl_val,
            })
    except Exception as e:
        logger.warning(f"save_history failed: {e}")

def get_download_url(session_id: str) -> Optional[str]:
    """Generate presigned URL for the final assembled document if it exists."""
    if not KB_BUCKET_NAME:
        return None
    try:
        key = f"outputs/{session_id}/FINAL_solution_design.md"
        s3.head_object(Bucket=KB_BUCKET_NAME, Key=key)
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": KB_BUCKET_NAME, "Key": key},
            ExpiresIn=3600,
        )
    except Exception:
        return None

# ── Endpoints ──────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "healthy", "service": "genapp-backend"}

@app.post("/api/agent", response_model=ChatResponse)
def run_agent(req: ChatRequest, user: dict = Depends(verify_token)):
    """Main endpoint — routes to multi-agent orchestrator."""
    try:
        history      = get_history(req.session_id)
        full_context = f"{history}\n\nUser: {req.query}" if history else req.query
        orchestrator = get_orchestrator()
        result       = orchestrator(
            f"session_id: {req.session_id}\n\n{full_context}"
        )
        answer = str(result)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(500, f"Agent error: {str(e)}")

    save_history(req.session_id, req.query, answer)
    download_url = get_download_url(req.session_id)

    return ChatResponse(
        answer=answer,
        sources=[],
        download_url=download_url,
    )

@app.get("/api/history/{session_id}")
def get_session_history(
    session_id: str, user: dict = Depends(verify_token)
):
    if not DYNAMODB_TABLE:
        return []
    table = dynamodb.Table(DYNAMODB_TABLE)
    return table.query(
        KeyConditionExpression=Key("session_id").eq(session_id)
    ).get("Items", [])

@app.get("/api/upload-url")
def get_upload_url(
    filename: str,
    session_id: str = "default",
    user: dict = Depends(verify_token),
):
    if not KB_BUCKET_NAME:
        raise HTTPException(500, "KB_BUCKET_NAME not configured")
    import mimetypes
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    key  = f"uploads/{session_id}/{filename}"
    url  = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": KB_BUCKET_NAME, "Key": key,
                "ContentType": content_type},
        ExpiresIn=3600,
    )
    return {"upload_url": url, "key": key, "filename": filename}

@app.post("/api/sync")
def sync_kb(user: dict = Depends(verify_token)):
    from tools.kb_tools import sync_knowledge_base
    result = sync_knowledge_base()
    return {"message": result}

@app.get("/api/download/{session_id}")
def get_document_url(session_id: str, user: dict = Depends(verify_token)):
    url = get_download_url(session_id)
    if not url:
        raise HTTPException(404, "Document not found for this session")
    return {"download_url": url}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
