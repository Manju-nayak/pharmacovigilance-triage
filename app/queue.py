
import os

from redis import Redis
from rq import Queue


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_connection = Redis.from_url(
    REDIS_URL,
    decode_responses=False,
    socket_connect_timeout=5,
    socket_timeout=5,
)

report_queue = Queue(
    name="pharmacovigilance",
    connection=redis_connection,
    default_timeout=300,
)


def enqueue_report(run_id: str, report_data: dict):
    """Add a report-processing job to Redis Queue."""

    return report_queue.enqueue(
        "app.worker.process_report",
        run_id,
        report_data,
        job_timeout=300,
        result_ttl=86400,
        failure_ttl=604800,
    )
