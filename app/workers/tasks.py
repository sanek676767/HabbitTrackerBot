from datetime import datetime, timezone

from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.debug_ping")
def debug_ping() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
