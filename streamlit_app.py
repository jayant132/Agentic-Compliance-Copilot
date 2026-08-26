"""
Minimal Streamlit frontend. Talks to FastAPI over HTTP only - never
imports from app/. In Phase 4 this becomes the real Approve/Reject screen.
"""

import requests
import streamlit as st

API_URL = "http://localhost:8000"

st.title("Compliance & Audit Readiness Agent")
st.caption("Phase 1: connectivity check only. No agents yet.")

if st.button("Check API health"):
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        st.json(resp.json())
    except requests.exceptions.ConnectionError:
        st.error("Could not reach the API. Is uvicorn running?")
