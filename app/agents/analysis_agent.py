"""
Risk & Gap Analysis Agent.

Responsibility: given retrieved evidence + a compliance question,
classify each relevant requirement as compliant / gap / partial, and
assign a risk level (low/medium/high). This agent does NOT retrieve
evidence itself - it only reasons over evidence it is given, which
keeps its responsibility narrow and testable.
"""

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.agents.common import run_agent_sync
from app.config import settings

analysis_agent = LlmAgent(
    name="risk_gap_agent",
    model=LiteLlm(model=settings.groq_model, reasoning_format="hidden"),
    instruction=(
        "You are a compliance risk analyst. You will be given a question "
        "and retrieved policy evidence. For each relevant requirement in "
        "the evidence:\n"
        "1. State whether the company's readiness is COMPLIANT, GAP, or "
        "PARTIAL (you may assume no contrary evidence means insufficient "
        "proof of compliance, i.e. a GAP).\n"
        "2. Assign a risk level: LOW, MEDIUM, or HIGH.\n"
        "3. Cite the exact source document for every claim.\n"
        "Do NOT invent requirements not present in the evidence. If the "
        "evidence does not address the question, say so explicitly instead "
        "of guessing."
    ),
)


def analyze_evidence(question: str, evidence: str) -> str:
    """Public entrypoint used by the workflow graph."""
    prompt = f"Question: {question}\n\nRetrieved evidence:\n{evidence}"
    return run_agent_sync(analysis_agent, prompt, app_name="analysis_agent_app")
