"""
Compliance Orchestrator Agent - Phase 2 version.

For now this agent has one tool (retrieve_policy_evidence) and answers
directly. In Phase 3 this same retrieval logic moves behind an A2A call
to a dedicated Evidence Agent.
"""

import asyncio

import litellm
litellm.drop_params = True

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types

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


root_agent = LlmAgent(
    name="compliance_orchestrator",
    model=LiteLlm(model=settings.groq_model, reasoning_format="hidden"),
    instruction=(
        "You are a compliance analyst assistant. ALWAYS call the "
        "retrieve_policy_evidence tool first for any compliance question. "
        "Answer ONLY using the retrieved evidence and cite the source "
        "document for every claim. If the evidence does not cover the "
        "question, say so explicitly instead of guessing."
    ),
    tools=[retrieve_policy_evidence],
)

_runner = InMemoryRunner(agent=root_agent, app_name="compliance_agent")


def ask_compliance_question(question: str, user_id: str = "cli_user") -> str:
    """Sync wrapper - used by the FastAPI route."""
    return asyncio.run(_ask_async(question, user_id))


async def _ask_async(question: str, user_id: str) -> str:
    session = await _runner.session_service.create_session(
        app_name="compliance_agent", user_id=user_id
    )
    final_text = ""
    async for event in _runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=question)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
    return final_text
