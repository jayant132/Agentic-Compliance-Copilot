"""
Compliance case workflow - explicit state machine via LangGraph.

Flow: RETRIEVE -> ANALYZE -> CRITIQUE -> FINALIZE

Why LangGraph instead of just calling 3 functions in a row:
Today this flow is linear, so a plain function would behave the same.
But Phase 4 adds a real branch (CRITIQUE can loop back to ANALYZE on
UNSUPPORTED) and a real pause (HUMAN_APPROVAL waits for an external
API call before FINALIZE runs). LangGraph gives us that branching /
pausing/resuming machinery for free - plain Python control flow does not.
"""

from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.agents.analysis_agent import analyze_evidence
from app.agents.critic_agent import critique_analysis
from app.agents.evidence_agent import get_evidence


class CaseState(TypedDict):
    question: str
    evidence: str
    findings: str
    critique: str
    final_result: str


def retrieve_node(state: CaseState) -> dict:
    evidence = get_evidence(state["question"])
    return {"evidence": evidence}


def analyze_node(state: CaseState) -> dict:
    findings = analyze_evidence(state["question"], state["evidence"])
    return {"findings": findings}


def critique_node(state: CaseState) -> dict:
    critique = critique_analysis(state["evidence"], state["findings"])
    return {"critique": critique}


def finalize_node(state: CaseState) -> dict:
    result = (
        f"FINDINGS:\n{state['findings']}\n\n"
        f"REVIEW:\n{state['critique']}"
    )
    return {"final_result": result}


def build_graph():
    graph = StateGraph(CaseState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("critique", critique_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", "critique")
    graph.add_edge("critique", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


compliance_graph = build_graph()


def run_compliance_case(question: str) -> dict:
    """Public entrypoint - runs the full graph for one question."""
    return compliance_graph.invoke({"question": question})
