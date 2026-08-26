"""
Deterministic guardrails - NOT LLM judgment calls.

Why deterministic: an LLM claiming "this is grounded" is itself an
unverified LLM claim. A real guardrail must be checkable in plain code.
"""

import re

NOT_COVERED_PHRASES = ["does not contain", "not covered", "no relevant evidence", "cannot provide an answer"]


def check_grounding(evidence: str, findings: str) -> tuple[bool, str]:
    """Block only if findings cite a source not present in evidence.

    A correct "the evidence doesn't cover this" answer is NOT a violation -
    it's the desired behavior when nothing relevant was retrieved. We only
    block when the model claims something ungrounded, not when it correctly
    declines to answer.
    """
    findings_lower = findings.lower()
    if any(phrase in findings_lower for phrase in NOT_COVERED_PHRASES):
        return True, "no evidence available - model correctly declined to answer"

    evidence_sources = set(re.findall(r"\[Source: ([\w\.\-]+)\]", evidence))
    cited_sources = set(re.findall(r"([\w\-]+_policy\.md)", findings))

    unsupported = cited_sources - evidence_sources
    if unsupported:
        return False, f"BLOCKED: findings cite sources not in retrieved evidence: {unsupported}"
    if not evidence_sources and not cited_sources:
        return False, "BLOCKED: no evidence was retrieved and no source was cited."
    return True, "grounded"


def needs_human_approval(findings: str) -> bool:
    """Any HIGH risk or GAP finding requires human sign-off before release."""
    text = findings.upper()
    return "HIGH" in text or "GAP" in text
