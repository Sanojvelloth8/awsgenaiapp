import streamlit as st
import requests
import os
import uuid
import time
import boto3

BACKEND_URL       = os.environ.get("BACKEND_URL", "http://localhost:8000")
COGNITO_POOL_ID   = os.environ.get("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID")
AWS_REGION        = os.environ.get("AWS_REGION", "us-east-1")

st.set_page_config(
    page_title="Architecture Assistant",
    page_icon="🏗️",
    layout="wide",
)

# ── Session state init ─────────────────────────────────────────────────────
for key, default in {
    "session_id":    str(uuid.uuid4()),
    "messages":      [],
    "authenticated": False,
    "access_token":  None,
    "refresh_token": None,
    "token_expiry":  0,
    "username":      "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Auth helpers ───────────────────────────────────────────────────────────
def login(username: str, password: str) -> bool:
    try:
        cognito  = boto3.client("cognito-idp", region_name=AWS_REGION)
        response = cognito.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
        auth = response.get("AuthenticationResult")
        if auth:
            st.session_state.authenticated = True
            st.session_state.username      = username
            st.session_state.access_token  = auth["IdToken"]
            st.session_state.refresh_token = auth.get("RefreshToken")
            st.session_state.token_expiry  = time.time() + 3500
            return True
    except Exception as e:
        st.error(f"Login failed: {e}")
    return False

def refresh_token_if_needed() -> None:
    if time.time() < st.session_state.token_expiry:
        return
    if not st.session_state.refresh_token:
        st.session_state.authenticated = False
        st.rerun()
    try:
        cognito  = boto3.client("cognito-idp", region_name=AWS_REGION)
        response = cognito.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": st.session_state.refresh_token},
        )
        auth = response.get("AuthenticationResult")
        if auth:
            st.session_state.access_token = auth["IdToken"]
            st.session_state.token_expiry = time.time() + 3500
    except Exception:
        st.session_state.authenticated = False
        st.rerun()

def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.access_token}"}

# ── Login screen ───────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    st.title("🏗️ Architecture Assistant")
    st.caption("Generate HLD, LLD, ADRs, and complete solution designs")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", use_container_width=True):
                if login(username, password):
                    st.rerun()
    st.stop()

refresh_token_if_needed()

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{st.session_state.username}**")
    st.divider()

    st.subheader("Upload documents")
    st.caption("Upload requirements, existing architecture docs, meeting notes")
    uploaded = st.file_uploader(
        "Choose file",
        type=["pdf", "txt", "docx", "md"],
        label_visibility="collapsed",
    )
    if uploaded and st.button("Upload & index", use_container_width=True):
        with st.spinner("Uploading..."):
            url_resp = requests.get(
                f"{BACKEND_URL}/api/upload-url",
                params={"filename": uploaded.name,
                        "session_id": st.session_state.session_id},
                headers=auth_headers(),
                timeout=30,
            )
            if url_resp.ok:
                import mimetypes
                content_type = mimetypes.guess_type(uploaded.name)[0] or "application/octet-stream"
                put_resp = requests.put(
                    url_resp.json()["upload_url"],
                    data=uploaded.getvalue(),
                    headers={"Content-Type": content_type},
                    timeout=120,
                )
                if put_resp.ok:
                    sync_resp = requests.post(
                        f"{BACKEND_URL}/api/sync",
                        headers=auth_headers(),
                        timeout=30,
                    )
                    st.success(f"'{uploaded.name}' uploaded. Indexing in ~2 min.")
                else:
                    st.error(f"Upload failed: {put_resp.status_code}")
            else:
                st.error(f"Could not get upload URL: {url_resp.text}")

    st.divider()

    st.subheader("Quick actions")
    if st.button("Generate full solution design", use_container_width=True):
        st.session_state.messages.append({
            "role": "user",
            "content": "Generate a complete solution design document based on the uploaded documents.",
        })
        st.rerun()

    if st.button("Generate HLD only", use_container_width=True):
        st.session_state.messages.append({
            "role": "user",
            "content": "Generate a High Level Design (HLD) document only.",
        })
        st.rerun()

    if st.button("Generate ADRs", use_container_width=True):
        st.session_state.messages.append({
            "role": "user",
            "content": "Generate Architecture Decision Records (ADRs) for all key design decisions.",
        })
        st.rerun()

    if st.button("New session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages   = []
        st.rerun()

    st.divider()
    if st.button("Sign out", use_container_width=True):
        for key in ["authenticated", "access_token", "refresh_token",
                    "token_expiry", "messages"]:
            st.session_state[key] = False if key == "authenticated" else None if "token" in key else 0 if "expiry" in key else []
        st.rerun()

# ── Main chat area ─────────────────────────────────────────────────────────
st.title("🏗️ Architecture Assistant")
st.caption(f"Session: `{st.session_state.session_id[:8]}...`")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("download_url"):
            st.download_button(
                "Download solution design (.md)",
                data=requests.get(msg["download_url"]).content,
                file_name="solution_design.md",
                mime="text/markdown",
            )

# ── Handle pending quick-action messages ──────────────────────────────────
pending = (
    st.session_state.messages
    and st.session_state.messages[-1]["role"] == "user"
    and not any(
        m["role"] == "assistant"
        for m in st.session_state.messages[
            st.session_state.messages.index(st.session_state.messages[-1]):
        ]
    )
)

# ── Chat input ─────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask a question or request a document section...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    pending = True

if pending and st.session_state.messages:
    last_user_msg = next(
        (m for m in reversed(st.session_state.messages) if m["role"] == "user"),
        None,
    )
    if last_user_msg:
        with st.chat_message("assistant"):
            with st.spinner("Agents working..."):
                resp = requests.post(
                    f"{BACKEND_URL}/api/agent",
                    json={
                        "query":      last_user_msg["content"],
                        "session_id": st.session_state.session_id,
                    },
                    headers=auth_headers(),
                    timeout=600,
                )
            if resp.ok:
                data   = resp.json()
                answer = data.get("answer", "")
                dl_url = data.get("download_url")
                st.markdown(answer)
                if dl_url:
                    st.download_button(
                        "Download solution design (.md)",
                        data=requests.get(dl_url).content,
                        file_name="solution_design.md",
                        mime="text/markdown",
                    )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "download_url": dl_url,
                })
            else:
                err = f"Error {resp.status_code}: {resp.text}"
                st.error(err)
                st.session_state.messages.append({
                    "role": "assistant", "content": err
                })
        st.rerun()
