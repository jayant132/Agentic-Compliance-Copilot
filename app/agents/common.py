"""
Shared helper for running any ADK LlmAgent synchronously.

Why this exists:
Every agent (Evidence, Analysis, Critic) needs the same
create-session -> send-message -> collect-final-text boilerplate.
Extracting it once means each agent file only defines *what* the
agent does (instruction + tools), not *how* to run it.
"""

import asyncio

import litellm
litellm.drop_params = True

from google.adk.runners import InMemoryRunner
from google.genai import types


def run_agent_sync(agent, message: str, app_name: str, user_id: str = "system") -> str:
    """Sync wrapper - runs an ADK agent once and returns its final text response."""
    return asyncio.run(_run_agent_async(agent, message, app_name, user_id))


async def _run_agent_async(agent, message: str, app_name: str, user_id: str) -> str:
    runner = InMemoryRunner(agent=agent, app_name=app_name)
    session = await runner.session_service.create_session(app_name=app_name, user_id=user_id)
    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=message)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
    return final_text
