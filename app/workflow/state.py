"""
Case state - short-lived workflow state stored in Redis (or fakeredis
for local dev without Docker).

Why Redis instead of a Python dict in memory:
FastAPI can run multiple worker processes, and this app will run in
Docker/production where the process can restart. In-memory state
would vanish or be invisible across workers. Redis gives every
worker/process a shared, fast view of "what state is this case in".

We store each case as one JSON blob per case_id, not multiple keys -
fewer round trips, and the whole case is naturally one unit of update.
"""

import json
import uuid
from datetime import datetime, timezone

import fakeredis

from app.config import settings

# Phase 3: using fakeredis (in-memory, same API as real Redis) since
# Docker isn't installed yet. Swap to redis.from_url(settings.redis_url)
# once Docker is available in Phase 5 - no other code changes needed,
# since we only ever call _redis.set/get/etc, which both clients
# implement identically.
_redis = fakeredis.FakeStrictRedis(decode_responses=True)

CASE_TTL_SECONDS = 60 * 60 * 24  # cases expire after 24h - this is workflow state, not an archive


def create_case(question: str) -> str:
    case_id = f"case_{uuid.uuid4().hex[:8]}"
    case = {
        "case_id": case_id,
        "question": question,
        "status": "IN_PROGRESS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
    }
    _redis.set(case_id, json.dumps(case), ex=CASE_TTL_SECONDS)
    return case_id


def get_case(case_id: str) -> dict | None:
    raw = _redis.get(case_id)
    return json.loads(raw) if raw else None


def update_case(case_id: str, **fields) -> None:
    case = get_case(case_id)
    if case is None:
        raise ValueError(f"Unknown case_id: {case_id}")
    case.update(fields)
    _redis.set(case_id, json.dumps(case), ex=CASE_TTL_SECONDS)
