# frontend

import streamlit as st
import requests
import os
import uuid
import boto3

# Configs
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
COGNITO_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

st.set_page_config(page_title="GenApp Chat", page_icon="🤖", layout="wide")

# Session states
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "access_token" not in st.session_state:
    st.session_state.access_token = None

# --- Auth ---
def login(username, password):
    try:
        cognito = boto3.client("cognito-idp", region_name=AWS_REGION)
        response = cognito.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password}
        )
        if response.get("AuthenticationResult"):
            st.session_state.authenticated = True
            st.session_state.username = username
            # Store the access token for API calls
            st.session_state.access_token = response["AuthenticationResult"]["IdToken"]
            return True
    except Exception as e:
        st.error(f"Login failed: {e}")
    return False

def get_auth_headers():
    """Get authorization headers with JWT token"""
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

if not st.session_state.authenticated:
    st.title("🔐 Login")
    with st.form("login"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if login(user, pwd):
                st.rerun()
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    
    st.subheader("Upload Document")
    file = st.file_uploader("Choose file", type=["pdf", "txt", "docx"])
    if file and st.button("Upload"):
        with st.spinner("Uploading..."):
            # Get presigned URL (with auth header)
            resp = requests.get(
                f"{BACKEND_URL}/api/upload-url", 
                params={"filename": file.name},
                headers=get_auth_headers()
            )
            if resp.ok:
                url = resp.json()["upload_url"]
                # Upload directly to S3
                requests.put(url, data=file.getvalue())
                st.success("Uploaded!")
                # Trigger sync (with auth header)
                requests.post(f"{BACKEND_URL}/api/sync", headers=get_auth_headers())
            else:
                st.error(f"Upload failed: {resp.text}")

    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.access_token = None
        st.rerun()

# --- Chat ---
st.title("🤖 GenApp Chat")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption(f"📚 {', '.join(msg['sources'])}")

if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        resp = requests.post(
            f"{BACKEND_URL}/api/chat", 
            json={
                "query": prompt,
                "session_id": st.session_state.session_id
            },
            headers=get_auth_headers()  # Include JWT token
        )
        if resp.ok:
            data = resp.json()
            with st.chat_message("assistant"):
                st.markdown(data["answer"])
                if data.get("sources"):
                    st.caption(f"📚 {', '.join(data['sources'])}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": data["answer"],
                "sources": data.get("sources", [])
            })
        else:
            st.error(f"Error: {resp.text}")
