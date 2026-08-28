# Agentic Compliance Copilot

**An AI agent system that assesses compliance readiness against internal policy documents — identifies gaps, assigns risk, and routes high-risk findings to a human for approval before release.**

Built to demonstrate production-oriented agentic AI engineering: multi-agent orchestration, explicit workflow state, an agent-to-agent network boundary, deterministic guardrails, human-in-the-loop approval, structured observability, and a measured evaluation suite with real numbers.

`Python` · `Google ADK` · `Groq (LiteLLM)` · `LangGraph` · `Pinecone` · `Redis` · `FastAPI` · `Streamlit` · `Docker`

---

## Why This Project

Most RAG portfolio projects stop at "retrieve and generate." This one models a real professional workflow — a compliance analyst assessing audit readiness — and implements the layers a production agentic system actually needs:

- Multiple specialized agents coordinated through an explicit state machine, not one prompt doing everything
- A real network boundary between agents (A2A pattern), not just Python function calls
- A **deterministic** guardrail that blocks ungrounded claims — not an LLM grading its own homework
- A genuine human-approval gate that pauses the workflow server-side
- Structured, per-node timing and logging — not just a final answer with no visibility into how it got there
- An evaluation harness with real, measured numbers — not invented ones

---

## Architecture

```
                            User question
                                  │
                                  ▼
                     FastAPI  →  POST /cases
                                  │
                                  ▼
                 LangGraph workflow (explicit state machine)
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
    RETRIEVE                  ANALYZE                   CRITIQUE
        │                         │                         │
        │  A2A (HTTP)             │                         │
        ▼                         ▼                         ▼
  Evidence Agent           Risk & Gap Agent            Critic Agent
  own FastAPI process      ADK + Groq                  ADK + Groq
  (port 8001)
        │
        ▼
  Pinecone — semantic search over chunked policy docs
                                  │
                                  ▼
                     Deterministic Guardrail
                (source-citation grounding check)
                       │                  │
                   BLOCKED             passes
                       │                  │
                       ▼                  ▼
              return to caller   Risk-based Approval Gate
                                          │
                          ┌───────────────┴───────────────┐
                          ▼                                ▼
                  PENDING_APPROVAL                     auto-DONE
                  (state in Redis)                (low risk / no gap)
                          │
             analyst calls /approve or /reject
                          │
                          ▼
                  Final grounded finding

Every node above is wrapped in a timed_step() context manager that logs
structured JSON (case_id, step, duration_ms, status) - this is what
produces the latency numbers reported below.
```

---

## Tech Stack — and Why Each Tool

| Technology | Role | Why this tool, not an alternative |
|---|---|---|
| **Google ADK** | Defines each agent's behavior, instructions, tools | Purpose-built for agent definition and tool-calling schemas, separate from workflow control |
| **Groq** (via LiteLLM) | LLM inference for all four agents | Free-tier, fast inference. LiteLLM makes the provider swappable (Gemini, OpenAI, etc.) in one line — ADK never hardcodes a provider |
| **LangGraph** | State machine: RETRIEVE → ANALYZE → CRITIQUE → FINALIZE | ADK governs *how one agent thinks*; LangGraph governs *what order steps run in* and supports branching/pausing — used for the human-approval pause — that plain function chaining can't give you |
| **Pinecone** | Vector store for policy document chunks | Purpose-built for semantic similarity search. Redis is deliberately **not** used for this |
| **Redis** (fakeredis locally) | Short-lived case & pending-approval state | Cheap, fast, ephemeral by design — matches "is this case waiting for approval" exactly. Not a system of record |
| **FastAPI** | HTTP boundary: submit case, check status, approve/reject | Lightweight, async, minimal boilerplate |
| **Streamlit** | Demo UI showing the approval step live | Pure HTTP client to the API — zero coupling to backend code |
| **Docker** | Reproducible deployment | Dockerfile + docker-compose for API, Evidence service, and Redis |

---

## The Four Agents

| # | Agent | Responsibility |
|---|---|---|
| 1 | **Compliance Orchestrator** | Entry point; drives the LangGraph workflow |
| 2 | **Evidence / Research Agent** | RAG only — retrieves relevant policy chunks from Pinecone, labeled by source. Runs as its own FastAPI process (port 8001) |
| 3 | **Risk & Gap Analysis Agent** | Classifies each requirement as COMPLIANT / GAP / PARTIAL and assigns risk (LOW / MEDIUM / HIGH), citing sources |
| 4 | **Critic / Review Agent** | Second reviewer — checks whether the analyst's conclusions are reasonable inferences or unsupported overreach |

---

## Agent-to-Agent Communication (A2A)

The Evidence Agent runs as an **independent process**, called over HTTP with a structured JSON message (`POST /a2a/evidence`) instead of a direct Python import. That's the essential A2A boundary: orchestrator and evidence agent could be owned by different teams, scaled independently, or replaced independently — a function call could never give you that.

> **Scope note:** this implements the *A2A pattern* — agent boundary as a network call with a defined message contract — via a lightweight FastAPI service, rather than Google's full A2A protocol/SDK (agent cards, discovery, auth). For one clean boundary in a small system, that trade-off is intentional. A production system with multiple teams/agents would adopt the full A2A spec for discovery and auth.

---

## Guardrails: Deterministic vs. LLM-Based

Two different kinds of "checking," used for different purposes:

- **Critic Agent** (LLM-based, soft signal) — judges whether the analysis is *reasonable* given the evidence. Useful, but an LLM's self-assessment is not a security boundary.
- **`check_grounding`** (deterministic, hard boundary) — parses the retrieved evidence and the analyst's findings with regex and **blocks** the case if the findings cite a source not present in retrieved evidence. Checkable in plain code, not a judgment call.

**Known limitation, documented rather than hidden:** the check for "the model correctly declined to answer" matches a fixed set of phrases in the Analysis Agent's output. This occasionally misses a valid decline phrased differently, causing an unnecessary `BLOCKED` result on a question with no relevant policy. This is a real brittleness of keyword-based NLP guardrails — a more robust version would check the Evidence Agent's retrieval similarity score directly instead of parsing the LLM's natural-language response.

---

## Human-in-the-Loop Approval

Any finding with a GAP or HIGH-risk classification routes to `PENDING_APPROVAL`, persisted in Redis. The workflow does not produce a final answer until a real API call is made:

```
POST /cases/{id}/approve
{ "decision": "APPROVE" }   or   { "decision": "REJECT" }
```

This is enforced server-side — not a "type YES to continue" prompt.

---

## Observability

Every LangGraph node is wrapped in a `timed_step()` context manager (`app/workflow/observability.py`) that emits structured JSON logs and records timing in an in-memory metrics store:

```json
{"case_id": "case_abc123", "step": "RETRIEVE", "duration_ms": 5784.4, "status": "ok"}
```

This is a deliberately lightweight substitute for a full OpenTelemetry/Langfuse setup — same underlying principle (span-style timing per unit of work), without standing up separate collector infrastructure to run and explain for a project this size. Swapping in a real backend later means changing what `timed_step` does internally, not how any node calls it.

### Measured Latency (real numbers)

Captured from 11 consecutive cases run after a performance fix (see below):

| Node | Avg latency |
|---|---|
| RETRIEVE (A2A call → Pinecone) | 5,784 ms |
| ANALYZE | 1,511 ms |
| CRITIQUE | 925 ms |
| FINALIZE | ~0 ms |
| **Total per case** | **8,228 ms** (min 7,666 ms / max 9,433 ms) |

**A real performance fix, found and verified with these metrics:** the first version of `get_pinecone_index()` created a brand-new Pinecone client and called `list_indexes()` on *every single retrieval* — a full network round-trip just to check an index that already existed. Once instrumented, this was visibly responsible for most of RETRIEVE's latency (originally averaging ~9,200 ms). Caching the Pinecone client and index handle at module load (`app/rag/ingest.py`) reduced average RETRIEVE latency to 5,784 ms — a measured ~37% improvement, found by reading the metrics, not by guessing.

**A second honest finding, from the same measurement process:** running the full 20-case eval end-to-end hits Groq's free-tier rate limit (8,000 tokens/minute) partway through, since 3 sequential LLM calls per case adds up quickly. This is why the latency numbers above are from **n=11** cases rather than the full 20 — a real constraint of the free tier, not a flaw in the pipeline. A production deployment would need a paid tier or request throttling between cases.

---

## Evaluation

Run against a 20-question labeled test set (`evals/eval_dataset.json`) covering all five policy documents plus questions with no relevant policy, to test resistance to hallucination.

| Metric | Result | Sample size |
|---|---|---|
| Retrieval accuracy | **20 / 20 (100%)** | 20 |
| Groundedness pass rate | **19 / 20 (95%)** | 20 |
| Hallucination rate | **1 / 20 (5%)** | 20 |
| Avg total latency / case | **8,228 ms** | 11 (rate-limited before completing all 20 — see Observability) |

- **Retrieval accuracy** — did Pinecone return the expected source document (or correctly return nothing relevant) for each question
- **Groundedness pass rate** — did the deterministic guardrail pass the finding as properly evidence-backed
- **Hallucination rate** — the inverse of groundedness, reframed to name the failure mode directly

The one failing groundedness case is the known limitation described above (a valid "not covered" answer parsed as ungrounded) — not a hallucinated finding.

> **On methodology:** this evaluates the pipeline end-to-end, not just retrieval — closer to *agent evaluation* than unit testing. Unit tests would check `check_grounding()` in isolation; this checks the full RETRIEVE → ANALYZE → CRITIQUE → GUARDRAIL chain against real questions.

---

## Project Structure

```
agentic-compliance-copilot/
├── app/
│   ├── agents/
│   │   ├── common.py            # shared ADK agent-runner helper
│   │   ├── orchestrator.py      # single-agent entry point (/ask)
│   │   ├── evidence_agent.py    # RAG agent
│   │   ├── evidence_service.py  # Evidence Agent as standalone FastAPI (A2A)
│   │   ├── analysis_agent.py    # risk & gap classification
│   │   └── critic_agent.py      # groundedness review
│   ├── rag/
│   │   ├── ingest.py            # chunk → embed → Pinecone upsert (cached client)
│   │   └── retrieve.py          # Pinecone query
│   ├── workflow/
│   │   ├── graph.py             # LangGraph state machine (instrumented)
│   │   ├── state.py             # Redis / fakeredis case state
│   │   ├── guardrails.py        # deterministic checks
│   │   └── observability.py     # structured logging + timing
│   ├── api/routes.py            # /health /ask /cases /cases/{id}/approve
│   ├── config.py                # typed settings from .env
│   └── main.py
├── data/                        # 5 synthetic compliance policy docs
├── evals/
│   ├── eval_dataset.json        # 20 labeled test cases
│   ├── run_eval.py              # retrieval + groundedness runner
│   └── run_eval_extended.py     # + latency + token/cost estimate
├── streamlit_app.py             # demo UI with approve / reject buttons
├── Dockerfile
├── docker-compose.yml           # api + evidence_service + redis
├── requirements.txt
└── .env.example
```

---

## Running It Locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # add your Groq + Pinecone keys

python -m app.rag.ingest        # one-time: embed policy docs into Pinecone
```

Then, in three separate terminals:

```bash
uvicorn app.agents.evidence_service:app --port 8001
uvicorn app.main:app --reload
streamlit run streamlit_app.py
```

## Running With Docker

```bash
docker-compose up --build
```

Spins up Redis, the Evidence Agent service, and the main API together.

---

## What Was Intentionally Not Built

- Full A2A SDK (agent cards, discovery) — one clean HTTP boundary was sufficient to demonstrate the pattern at this scale
- Full OpenTelemetry/Langfuse observability stack — structured timed logs demonstrate the same principle without separate infrastructure
- PostgreSQL — no need for permanent storage beyond short-lived case state
- Auth/IAM, CI/CD, Kafka/Celery — explicitly out of scope for a single-analyst proof of concept; natural next additions at team scale

---

## License

MIT
