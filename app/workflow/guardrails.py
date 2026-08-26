"""
Deterministic guardrails - NOT LLM judgment calls.

Why deterministic: an LLM claiming "this is grounded" is itself an
unverified LLM claim. A real guardrail must be checkable in plain code.
"""

import re


def check_grounding(evidence: str, findings: str) -> tuple[bool, str]:
    """Block if findings cite a source document not present in evidence."""
    evidence_sources = set(re.findall(r"\[Source: ([\w\.\-]+)\]", evidence))
    cited_sources = set(re.findall(r"([\w\-]+_policy\.md)", findings))

    unsupported = cited_sources - evidence_sources
    if unsupported:
        return False, f"BLOCKED: findings cite sources not in retrieved evidence: {unsupported}"
    if not evidence_sources:
        return False, "BLOCKED: no evidence was retrieved to support any finding."
    return True, "grounded"


def needs_human_approval(findings: str) -> bool:
    """Any HIGH risk or GAP finding requires human sign-off before release."""
    text = findings.upper()
    return "HIGH" in text or "GAP" in text
