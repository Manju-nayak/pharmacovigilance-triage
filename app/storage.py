
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def quarantine_record(body, errors, request_id):
    """Save a rejected request and its validation errors."""

    quarantine_dir = Path(
        os.getenv("QUARANTINE_DIR", "data/quarantine")
    )
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "quarantine_id": str(uuid4()),
        "request_id": request_id,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "body": body,
        "errors": errors,
        "status": "rejected",
    }

    destination = quarantine_dir / (
        f"{record['quarantine_id']}.json"
    )

    destination.write_text(
        json.dumps(record, indent=2, default=str),
        encoding="utf-8",
    )

    return record
