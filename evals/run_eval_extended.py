"""
Extended evaluation - retrieval, groundedness, latency, and token/cost
estimates, all from real measured runs (not invented numbers).
"""

import json
import statistics

from app.rag.retrieve import retrieve_evidence
from app.workflow.guardrails import check_grounding
from app.workflow.graph import run_compliance_case
from app.workflow.observability import get_metrics, clear_metrics

# Groq gpt-oss-120b pricing (per 1M tokens) - update if pricing changes.
# Source: groq.com/pricing at time of writing. Stated explicitly so the
# cost estimate is traceable to a real number, not guessed.
INPUT_COST_PER_1M = 0.15
OUTPUT_COST_PER_1M = 0.75
AVG_TOKENS_PER_CALL_ESTIMATE = 800  # rough input+output estimate per LLM call, see note below

cases = json.load(open("evals/eval_dataset.json"))
retrieval_hits, groundedness_hits, total = 0, 0, len(cases)
clear_metrics()

for i, c in enumerate(cases):
    results = retrieve_evidence(c["question"], top_k=3)
    sources = [r["source"] for r in results]
    if c["expect_source"] is None or c["expect_source"] in sources:
        retrieval_hits += 1

    case_id = f"eval_{i}"
    state = run_compliance_case(c["question"], case_id=case_id)
    ok, _ = check_grounding(state["evidence"], state["findings"])
    if ok:
        groundedness_hits += 1

metrics = get_metrics()
totals = [m["duration_ms"] for m in metrics if m["step"] == "TOTAL"]
node_latencies = {}
for step in ["RETRIEVE", "ANALYZE", "CRITIQUE", "FINALIZE"]:
    vals = [m["duration_ms"] for m in metrics if m["step"] == step]
    if vals:
        node_latencies[step] = round(statistics.mean(vals), 1)

llm_calls_per_case = 3  # evidence + analyze + critique
estimated_calls = total * llm_calls_per_case
estimated_tokens = estimated_calls * AVG_TOKENS_PER_CALL_ESTIMATE
estimated_cost = (estimated_tokens / 1_000_000) * ((INPUT_COST_PER_1M + OUTPUT_COST_PER_1M) / 2)

print("=" * 50)
print("RETRIEVAL & GROUNDEDNESS")
print("=" * 50)
print(f"Retrieval accuracy:      {retrieval_hits}/{total} ({100*retrieval_hits/total:.0f}%)")
print(f"Groundedness pass rate:  {groundedness_hits}/{total} ({100*groundedness_hits/total:.0f}%)")
print(f"Hallucination rate:      {total-groundedness_hits}/{total} ({100*(total-groundedness_hits)/total:.0f}%)")

print()
print("=" * 50)
print("LATENCY (measured, milliseconds)")
print("=" * 50)
if totals:
    print(f"Avg total latency/case:  {statistics.mean(totals):.0f} ms")
    print(f"P95 total latency/case:  {statistics.quantiles(totals, n=20)[18]:.0f} ms" if len(totals) >= 5 else f"P95: (need 5+ samples, have {len(totals)})")
    print(f"Min / Max:               {min(totals):.0f} ms / {max(totals):.0f} ms")
print("Per-node avg latency:")
for step, ms in node_latencies.items():
    print(f"  {step:10s} {ms:.0f} ms")

print()
print("=" * 50)
print("COST ESTIMATE (approximate - see note)")
print("=" * 50)
print(f"LLM calls in this run:   {estimated_calls} (3 per case: evidence+analyze+critique)")
print(f"Estimated tokens:        ~{estimated_tokens:,.0f} (using {AVG_TOKENS_PER_CALL_ESTIMATE}/call average estimate)")
print(f"Estimated cost:          ~${estimated_cost:.4f} (Groq gpt-oss-120b blended rate)")
print("NOTE: token count is an estimate, not measured from API responses.")
print("      LiteLLM's response.usage field would give exact counts - see")
print("      README for how to wire that in as a follow-up improvement.")
