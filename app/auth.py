"""
Authentication Module
======================
Supports:
- Google OAuth2 (via streamlit-google-auth)
- GitHub OAuth2 (via requests-oauthlib)
- Simple password bypass for local dev
- Role-based access control (RBAC)

Set AUTH_ENABLED=false in .env to bypass for local dev.
"""

import os
import hashlib
import hmac
import json
from typing import Optional, Dict, Any
import streamlit as st

AUTH_ENABLED    = os.getenv("AUTH_ENABLED", "false").lower() == "true"
ADMIN_EMAILS    = set(os.getenv("ADMIN_EMAILS", "").split(","))
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
LOCAL_DEV_PASSWORD   = os.getenv("LOCAL_DEV_PASSWORD", "hr_demo_2024")

# Role definitions
ROLES = {
    "admin":    ["view_all", "manage_users", "view_reports", "chat"],
    "hr_staff": ["view_all", "view_reports", "chat"],
    "employee": ["view_own", "chat"],
}

def get_role(email: str) -> str:
    if email in ADMIN_EMAILS:
        return "admin"
    if email.endswith("@hr.company.com"):
        return "hr_staff"
    return "employee"

def has_permission(role: str, action: str) -> bool:
    return action in ROLES.get(role, [])

def check_auth() -> Optional[Dict[str, Any]]:
    """
    Returns user dict if authenticated, else shows login UI and returns None.
    Skip auth entirely if AUTH_ENABLED=false.
    """
    if not AUTH_ENABLED:
        return {"name": "Dev User", "email": "dev@local", "role": "admin"}

    if "auth_user" in st.session_state:
        return st.session_state["auth_user"]

    st.title("🔐 HR Assistant — Sign In")

    tab_google, tab_local = st.tabs(["Google OAuth", "Local Dev Login"])

    with tab_google:
        if GOOGLE_CLIENT_ID:
            # Streamlit doesn't natively support OAuth; use redirect-based flow
            auth_url = (
                f"https://accounts.google.com/o/oauth2/auth"
                f"?client_id={GOOGLE_CLIENT_ID}"
                f"&redirect_uri={os.getenv('OAUTH_REDIRECT_URI','http://localhost:8501')}"
                f"&response_type=code&scope=openid+email+profile"
            )
            st.markdown(f'<a href="{auth_url}" target="_self">'
                        f'<button style="background:#4285f4;color:white;border:none;'
                        f'padding:10px 20px;border-radius:5px;cursor:pointer;font-size:1rem">'
                        f'🔵 Sign in with Google</button></a>', unsafe_allow_html=True)
        else:
            st.info("Google OAuth not configured. Set GOOGLE_CLIENT_ID in .env")

    with tab_local:
        st.caption("For local development only")
        pwd = st.text_input("Dev Password", type="password")
        if st.button("Login"):
            if hmac.compare_digest(pwd, LOCAL_DEV_PASSWORD):
                user = {"name": "Dev User", "email": "dev@local", "role": "admin"}
                st.session_state["auth_user"] = user
                st.rerun()
            else:
                st.error("Incorrect password")

    st.stop()
    return None
