
import json
import os
from datetime import datetime, timezone

import redis


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RUN_KEY_PREFIX = "pharmacovigilance:run:"


def get_redis_client():
    """Create a Redis connection."""
    return redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def create_run(run_id: str, case_id: str):
    """Create a new run record with queued status."""
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "run_id": run_id,
        "case_id": case_id,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "result": None,
        "error": None,
    }

    client = get_redis_client()
    client.set(
        f"{RUN_KEY_PREFIX}{run_id}",
        json.dumps(record),
    )

    return record


def get_run(run_id: str):
    """Retrieve a run record."""
    client = get_redis_client()
    record = client.get(f"{RUN_KEY_PREFIX}{run_id}")

    if record is None:
        return None

    return json.loads(record)


def update_run(run_id: str, **updates):
    """Update selected fields in a run record."""
    record = get_run(run_id)

    if record is None:
        return None

    record.update(updates)
    record["updated_at"] = datetime.now(timezone.utc).isoformat()

    client = get_redis_client()
    client.set(
        f"{RUN_KEY_PREFIX}{run_id}",
        json.dumps(record, default=str),
    )

    return record
