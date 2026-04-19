"""
Celery worker configuration for async tasks.

Handles:
- Background wall analysis for large cases
- Job queue management via Redis
- Task tracking and retry logic
"""

from celery import Celery, Task
from celery.result import AsyncResult
import logging

from junior.core import settings, get_logger

logger = get_logger(__name__)

# Create Celery app
app = Celery(
    "junior",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["application/json"],
    result_serializer="json",
    timezone=settings.celery_timezone if hasattr(settings, 'celery_timezone') else "UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)


class CallbackTask(Task):
    """Task with result callback support."""

    def on_success(self, retval, task_id, args, kwargs):
        """Success callback."""
        logger.info(f"✅ Task {task_id} completed successfully")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Retry callback."""
        logger.warning(f"⚠️  Task {task_id} retrying: {exc}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback."""
        logger.error(f"❌ Task {task_id} failed: {exc}", exc_info=einfo)


# Register base task class
app.Task = CallbackTask


@app.task(bind=True, name="analyze_wall_async")
def analyze_wall_async(self, case_id: str, nodes_data: list, edges_data: list, context: str = ""):
    """
    Async task: Analyze detective wall in background.

    Args:
        case_id: Case ID
        nodes_data: Wall nodes
        edges_data: Wall edges
        context: Case context

    Returns:
        Analysis result dict
    """
    try:
        logger.info(f"🚀 Starting async wall analysis: case={case_id} task={self.request.id}")

        # Update task state
        self.update_state(state="PROGRESS", meta={"current": 0, "total": 100})

        # Import here to avoid circular imports
        import asyncio
        from junior.services.wall_service import get_wall_service
        from junior.api.schemas import (
            DetectiveWallAnalyzeRequest,
            DetectiveWallNode,
            DetectiveWallEdge,
        )

        # Create request object
        nodes = [DetectiveWallNode(**n) for n in nodes_data]
        edges = [DetectiveWallEdge(**e) for e in edges_data]
        request = DetectiveWallAnalyzeRequest(
            nodes=nodes,
            edges=edges,
            case_context=context,
        )

        # Run async analysis
        loop = asyncio.get_event_loop()
        service = loop.run_until_complete(get_wall_service())
        result = loop.run_until_complete(service.analyze(request, case_id=case_id))

        self.update_state(state="PROGRESS", meta={"current": 100, "total": 100})

        logger.info(f"✅ Wall analysis completed: case={case_id}")
        return result.model_dump()

    except Exception as exc:
        logger.error(f"❌ Wall analysis failed: {exc}", exc_info=True)
        raise


@app.task(bind=True, name="save_wall_snapshot_async")
def save_wall_snapshot_async(self, case_id: str, nodes_data: list, edges_data: list):
    """
    Async task: Save wall snapshot to persistent storage.

    Args:
        case_id: Case ID
        nodes_data: Wall nodes
        edges_data: Wall edges

    Returns:
        Snapshot ID
    """
    try:
        logger.info(f"💾 Saving wall snapshot: case={case_id}")

        import asyncio
        from junior.services.wall_service import get_wall_service

        loop = asyncio.get_event_loop()
        service = loop.run_until_complete(get_wall_service())
        snapshot_id = loop.run_until_complete(
            service.save_snapshot(
                case_id=case_id,
                nodes=nodes_data,
                edges=edges_data,
            )
        )

        logger.info(f"✅ Snapshot saved: {snapshot_id}")
        return {"snapshot_id": snapshot_id}

    except Exception as exc:
        logger.error(f"❌ Snapshot save failed: {exc}")
        raise


@app.task(name="clear_cache_async")
def clear_cache_async(namespace: str = "wall:analysis"):
    """
    Async task: Clear cache entries.

    Args:
        namespace: Redis namespace to clear

    Returns:
        Number of entries cleared
    """
    try:
        logger.info(f"🧹 Clearing cache: {namespace}")

        import asyncio
        from junior.db import get_redis_client

        loop = asyncio.get_event_loop()
        redis = loop.run_until_complete(get_redis_client())
        cleared = loop.run_until_complete(redis.clear_namespace(namespace=namespace))

        logger.info(f"✅ Cache cleared: {cleared} entries")
        return {"cleared": cleared}

    except Exception as exc:
        logger.error(f"❌ Cache clear failed: {exc}")
        raise


def get_task_status(task_id: str) -> dict:
    """Get status of async task."""
    result = AsyncResult(task_id, app=app)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.successful() else None,
        "error": str(result.info) if result.failed() else None,
        "progress": result.info if result.state == "PROGRESS" else None,
    }


def cancel_task(task_id: str) -> bool:
    """Cancel a running task."""
    result = AsyncResult(task_id, app=app)
    result.revoke(terminate=True)
    logger.info(f"Task cancelled: {task_id}")
    return True
