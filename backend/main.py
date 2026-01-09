# backend

import os
import time
import json
import boto3
import httpx
from boto3.dynamodb.conditions import Key
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError

# === Config ===
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
KB_ID = os.environ.get("KB_ID")
KB_BUCKET_NAME = os.environ.get("KB_BUCKET_NAME")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID")
MODEL_ID = "amazon.titan-text-express-v1"
RELEVANCE_THRESHOLD = 0.3
HISTORY_LIMIT = 6  # Keep last 6 messages (3 turns) for context

# === AWS Clients ===
bedrock_agent = boto3.client("bedrock-agent", region_name=AWS_REGION)
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

# === JWT Validation ===
security = HTTPBearer(auto_error=False)
_jwks_cache = None

def get_cognito_jwks():
    """Fetch and cache Cognito JWKS (JSON Web Key Set)"""
    global _jwks_cache
    if _jwks_cache is None:
        jwks_url = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
        response = httpx.get(jwks_url)
        _jwks_cache = response.json()
    return _jwks_cache

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validate JWT token from Cognito"""
    if not COGNITO_USER_POOL_ID or not COGNITO_CLIENT_ID:
        # Skip validation if Cognito not configured (for local dev)
        return {"sub": "anonymous"}
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    token = credentials.credentials
    
    try:
        # Get JWKS
        jwks = get_cognito_jwks()
        
        # Decode token header to get key id
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        # Find matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break
        
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid token: key not found")
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
        )
        
        return payload
        
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

# === FastAPI App ===
app = FastAPI(title="GenAppAWS Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# === Models ===
class ChatRequest(BaseModel):
    query: str
    session_id: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]

# === Helper: Get conversation history ===
def get_history(session_id: str, limit: int = HISTORY_LIMIT) -> str:
    if not DYNAMODB_TABLE:
        return ""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.query(
            KeyConditionExpression=Key("session_id").eq(session_id),
            ScanIndexForward=False,  # Newest first
            Limit=limit
        )
        items = response.get("Items", [])
        items.reverse()  # Oldest first for context
        
        history_lines = []
        for item in items:
            role = item.get("role", "")
            content = item.get("content", "")
            if role == "user":
                history_lines.append(f"User: {content}")
            else:
                history_lines.append(f"Assistant: {content}")
        return "\n".join(history_lines)
    except:
        return ""

# === Endpoints ===
@app.get("/")
def health():
    return {"status": "healthy", "model": MODEL_ID}

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user: dict = Depends(verify_token)):
    if not KB_ID:
        raise HTTPException(500, "KB_ID not configured")

    try:
        # Get conversation history for memory
        history = get_history(req.session_id)
        
        # Step 1: Retrieve from Knowledge Base
        retrieve_response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": req.query},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 3}}
        )
        
        results = retrieve_response.get("retrievalResults", [])
        relevant_results = [r for r in results if r.get("score", 0) >= RELEVANCE_THRESHOLD]
        
        contexts = [r["content"]["text"] for r in relevant_results]
        sources = list({r.get("location", {}).get("s3Location", {}).get("uri", "").split("/")[-1] for r in relevant_results if r.get("location")})
        context_str = "\n\n".join(contexts) if contexts else ""

        # Build prompt with memory
        history_section = f"\nPrevious conversation:\n{history}\n" if history else ""
        
        if context_str:
            prompt = f"""You are a helpful assistant with memory of our conversation.
{history_section}
Document context:
{context_str}

User: {req.query}

Provide a helpful answer based on the context and our conversation:"""
        else:
            prompt = f"""You are a helpful assistant with memory of our conversation.
{history_section}
User: {req.query}

Answer using your general knowledge:"""
            sources = []

        # Generate response with Titan
        body = json.dumps({
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 2000,
                "temperature": 0.7,
                "topP": 0.95
            }
        })

        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(response["body"].read())
        answer = response_body["results"][0]["outputText"].strip()

    except Exception as e:
        raise HTTPException(500, f"Bedrock error: {str(e)}")

    # Save to DynamoDB
    if DYNAMODB_TABLE:
        table = dynamodb.Table(DYNAMODB_TABLE)
        ts = int(time.time() * 1000)
        table.put_item(Item={"session_id": req.session_id, "timestamp": ts, "role": "user", "content": req.query, "ttl": int(time.time()) + 604800})
        table.put_item(Item={"session_id": req.session_id, "timestamp": ts + 1, "role": "assistant", "content": answer, "sources": sources, "ttl": int(time.time()) + 604800})

    return ChatResponse(answer=answer, sources=sources)

@app.get("/api/history/{session_id}")
def get_session_history(session_id: str, user: dict = Depends(verify_token)):
    if not DYNAMODB_TABLE:
        return []
    table = dynamodb.Table(DYNAMODB_TABLE)
    return table.query(KeyConditionExpression=Key("session_id").eq(session_id)).get("Items", [])

@app.get("/api/upload-url")
def get_upload_url(filename: str, user: dict = Depends(verify_token)):
    if not KB_BUCKET_NAME:
        raise HTTPException(500, "KB_BUCKET_NAME not configured")
    url = s3.generate_presigned_url("put_object", Params={"Bucket": KB_BUCKET_NAME, "Key": filename}, ExpiresIn=3600)
    return {"upload_url": url, "filename": filename}

@app.post("/api/sync")
def sync_kb(user: dict = Depends(verify_token)):
    if not KB_ID:
        return {"error": "KB_ID not configured"}
    ds = bedrock_agent.list_data_sources(knowledgeBaseId=KB_ID, maxResults=1)
    if ds.get("dataSourceSummaries"):
        job = bedrock_agent.start_ingestion_job(knowledgeBaseId=KB_ID, dataSourceId=ds["dataSourceSummaries"][0]["dataSourceId"])
        return {"job_id": job["ingestionJob"]["ingestionJobId"], "status": job["ingestionJob"]["status"]}
    return {"error": "No data source found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
