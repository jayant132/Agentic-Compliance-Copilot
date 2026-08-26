"""
Agentic Compliance Copilot - demo UI.

Talks to FastAPI only via HTTP (no direct imports from app/) - this
mirrors how a real frontend would integrate with the backend.
"""

import time
import requests
import streamlit as st

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Agentic Compliance Copilot", layout="centered")
st.title("🛡️ Agentic Compliance Copilot")
st.caption("RAG + multi-agent analysis + guardrails + human-in-the-loop approval")

if "case_id" not in st.session_state:
    st.session_state.case_id = None
    st.session_state.status = None

st.subheader("1. Ask a compliance question")
question = st.text_input(
    "Question", value="What are the MFA requirements?",
    placeholder="e.g. How quickly must a breach be reported?"
)

if st.button("Run Compliance Assessment", type="primary"):
    with st.spinner("Retrieving evidence → analyzing → critiquing → guardrail check..."):
        try:
            resp = requests.post(f"{API_URL}/cases", json={"question": question}, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            st.session_state.case_id = data["case_id"]
            st.session_state.status = data["status"]
        except requests.exceptions.RequestException as e:
            st.error(f"Could not reach the API: {e}")

if st.session_state.case_id:
    st.divider()
    st.subheader("2. Case status")
    case = requests.get(f"{API_URL}/cases/{st.session_state.case_id}").json()
    status = case["status"]

    st.write(f"**Case ID:** `{case['case_id']}`")

    if status == "PENDING_APPROVAL":
        st.warning("⏸️ PENDING HUMAN APPROVAL — a HIGH risk / GAP finding requires sign-off before release.")
        with st.expander("View draft finding (pre-approval)"):
            st.text(case["result"])

        col1, col2 = st.columns(2)
        if col1.button("✅ Approve", use_container_width=True):
            requests.post(
                f"{API_URL}/cases/{case['case_id']}/approve",
                json={"decision": "APPROVE"}, timeout=30,
            )
            st.rerun()
        if col2.button("❌ Reject", use_container_width=True):
            requests.post(
                f"{API_URL}/cases/{case['case_id']}/approve",
                json={"decision": "REJECT"}, timeout=30,
            )
            st.rerun()

    elif status == "BLOCKED":
        st.error("🚫 BLOCKED by guardrail — finding was not sufficiently grounded in evidence.")
        st.text(case["result"])

    elif status == "DONE":
        st.success("✅ APPROVED — final compliance finding")
        st.text(case["result"])

    elif status == "REJECTED":
        st.error("❌ Rejected by reviewer — finding withheld.")

    else:
        st.info(f"Status: {status}")
