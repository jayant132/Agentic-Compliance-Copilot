"""
Compliance case workflow - explicit state machine via LangGraph.

Flow: RETRIEVE -> ANALYZE -> CRITIQUE -> FINALIZE

Why LangGraph instead of just calling 3 functions in a row:
Today this flow is linear, so a plain function would behave the same.
But Phase 4 adds a real branch (CRITIQUE can loop back to ANALYZE on
UNSUPPORTED) and a real pause (HUMAN_APPROVAL waits for an external
API call before FINALIZE runs). LangGraph gives us that branching /
pausing/resuming machinery for free - plain Python control flow does not.

Phase 5 adds timing/logging around every node via timed_step, so we can
report real latency numbers instead of estimates.
"""

from typing import TypedDict

from langgraph.graph import StateGraph, END
import requests

from app.agents.analysis_agent import analyze_evidence
from app.agents.critic_agent import critique_analysis
from app.workflow.observability import timed_step


class CaseState(TypedDict):
    case_id: str
    question: str
    evidence: str
    findings: str
    critique: str
    final_result: str


def retrieve_node(state: CaseState) -> dict:
    with timed_step(state["case_id"], "RETRIEVE"):
        evidence = requests.post(
            "http://localhost:8001/a2a/evidence",
            json={"question": state["question"]}, timeout=30,
        ).json()["evidence"]
    return {"evidence": evidence}


def analyze_node(state: CaseState) -> dict:
    with timed_step(state["case_id"], "ANALYZE"):
        findings = analyze_evidence(state["question"], state["evidence"])
    return {"findings": findings}


def critique_node(state: CaseState) -> dict:
    with timed_step(state["case_id"], "CRITIQUE"):
        critique = critique_analysis(state["evidence"], state["findings"])
    return {"critique": critique}


def finalize_node(state: CaseState) -> dict:
    with timed_step(state["case_id"], "FINALIZE"):
        result = f"FINDINGS:\n{state['findings']}\n\nREVIEW:\n{state['critique']}"
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


def run_compliance_case(question: str, case_id: str = "unscoped") -> dict:
    """Public entrypoint - runs the full graph for one question."""
    with timed_step(case_id, "TOTAL"):
        result = compliance_graph.invoke({"case_id": case_id, "question": question})
    return result
