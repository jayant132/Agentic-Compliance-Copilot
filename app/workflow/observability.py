"""
Lightweight observability - structured logging + timing.

Why not full OpenTelemetry/Langfuse: this project is intentionally
small. Structured JSON logs + a simple in-memory metrics collector give
us real, inspectable numbers (latency, tokens, node transitions) without
standing up separate observability infrastructure to explain/maintain.
The pattern (log every node transition with timing) is the same
principle OpenTelemetry spans use - just without the collector backend.
"""

import json
import logging
import time
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("compliance_agent")

# In-memory metrics store for the current process - good enough for a
# single-instance demo. A production system would ship these to a real
# metrics backend (Prometheus, Langfuse, etc).
_metrics: list[dict] = []


@contextmanager
def timed_step(case_id: str, step_name: str):
    """Times a block of code and logs + records it as a structured event."""
    start = time.time()
    error = None
    try:
        yield
    except Exception as e:
        error = str(e)
        raise
    finally:
        duration_ms = round((time.time() - start) * 1000, 1)
        event = {
            "case_id": case_id,
            "step": step_name,
            "duration_ms": duration_ms,
            "status": "error" if error else "ok",
        }
        if error:
            event["error"] = error
        logger.info(json.dumps(event))
        _metrics.append(event)


def get_metrics() -> list[dict]:
    return list(_metrics)


def clear_metrics() -> None:
    _metrics.clear()
