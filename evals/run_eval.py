"""Evaluation runner - measures retrieval accuracy and groundedness."""
import json
from app.rag.retrieve import retrieve_evidence
from app.workflow.guardrails import check_grounding
from app.workflow.graph import run_compliance_case

cases = json.load(open("evals/eval_dataset.json"))
retrieval_hits, groundedness_hits, total = 0, 0, len(cases)

for c in cases:
    results = retrieve_evidence(c["question"], top_k=3)
    sources = [r["source"] for r in results]
    if c["expect_source"] is None or c["expect_source"] in sources:
        retrieval_hits += 1

    state = run_compliance_case(c["question"])
    ok, _ = check_grounding(state["evidence"], state["findings"])
    if ok:
        groundedness_hits += 1

print(f"Retrieval accuracy: {retrieval_hits}/{total} ({100*retrieval_hits/total:.0f}%)")
print(f"Groundedness pass rate: {groundedness_hits}/{total} ({100*groundedness_hits/total:.0f}%)")
