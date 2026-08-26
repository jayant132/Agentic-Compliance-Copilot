"""
Critic/Review Agent.

Responsibility: the "second reviewer" - checks whether the analysis
agent's conclusions are reasonable inferences from the evidence given,
or whether it overreached / invented something not grounded in it.
This is a *soft* (LLM-based) check; Phase 4 adds a *deterministic*
guardrail on top for things that must never be trusted to an LLM's
judgment alone (e.g. verifying cited sources actually exist in the
retrieved evidence set).
"""

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.agents.common import run_agent_sync
from app.config import settings

critic_agent = LlmAgent(
    name="critic_agent",
    model=LiteLlm(model=settings.groq_model, reasoning_format="hidden"),
    instruction=(
        "You are a compliance reviewer checking an analyst's findings "
        "against retrieved evidence. Compliance analysis REQUIRES drawing "
        "reasonable inferences (e.g. 'policy requires X, no evidence of "
        "implementation was provided, therefore this is a GAP' is a valid, "
        "expected inference - not an unsupported claim).\n\n"
        "Mark UNSUPPORTED only if the findings:\n"
        "- cite a source document that isn't in the evidence, OR\n"
        "- state a policy requirement that isn't in the evidence, OR\n"
        "- directly contradict something the evidence says.\n\n"
        "Reasonable risk/gap judgment calls based on the evidence are "
        "SUPPORTED. Respond with:\n"
        "VERDICT: SUPPORTED or VERDICT: UNSUPPORTED\n"
        "Then a short explanation."
    ),
)


def critique_analysis(evidence: str, findings: str) -> str:
    """Public entrypoint used by the workflow graph."""
    prompt = f"Evidence:\n{evidence}\n\nAnalyst findings:\n{findings}"
    return run_agent_sync(critic_agent, prompt, app_name="critic_agent_app")
