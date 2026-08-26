"""
Evidence/Research Agent.

Responsibility: RAG only. Given a compliance question, retrieve the
most relevant policy chunks from Pinecone, each labeled with its
source document.

In Phase 3C this exact function gets fronted by an A2A server so the
Orchestrator calls it as a message instead of a direct import.
"""

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.agents.common import run_agent_sync
from app.config import settings
from app.rag.retrieve import retrieve_evidence


def retrieve_policy_evidence(query: str) -> str:
    """Retrieve relevant compliance policy evidence for a topic or question.

    Args:
        query: The compliance topic or question, e.g. "password requirements".

    Returns:
        Matching policy text chunks, each labeled with its source document.
    """
    results = retrieve_evidence(query, top_k=3)
    if not results:
        return "No relevant evidence found in the knowledge base."
    return "\n\n".join(f"[Source: {r['source']}]\n{r['text']}" for r in results)


evidence_agent = LlmAgent(
    name="evidence_agent",
    model=LiteLlm(model=settings.groq_model, reasoning_format="hidden"),
    instruction=(
        "You retrieve compliance policy evidence. ALWAYS call the "
        "retrieve_policy_evidence tool for the given question and return "
        "exactly what it returns, unmodified - do not summarize or add "
        "commentary. If no evidence is found, say so explicitly."
    ),
    tools=[retrieve_policy_evidence],
)


def get_evidence(question: str) -> str:
    """Public entrypoint used by the workflow graph."""
    return run_agent_sync(evidence_agent, question, app_name="evidence_agent_app")
