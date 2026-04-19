"""Detective Wall endpoints

Provides an API to analyze the current detective wall canvas (nodes + edges)
using the DetectiveWallAgent with Redis caching.

Includes both sync and async analysis options.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from junior.core import get_logger
from junior.core.exceptions import ConfigurationError
from junior.services.wall_service import get_wall_service
from junior.api.endpoints import auth
from junior.api.schemas import (
    DetectiveWallAnalyzeRequest,
    DetectiveWallAnalyzeResponse,
    HealthResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/analyze", response_model=DetectiveWallAnalyzeResponse)
async def analyze_wall(
    request: DetectiveWallAnalyzeRequest,
    case_id: str = Query("", description="Optional case ID for persistence"),
    force_refresh: bool = Query(False, description="Skip cache and re-analyze"),
):
    """Analyze detective wall with caching and proactive suggestions.

    Args:
        request: Wall analysis request (nodes, edges, case context)
        case_id: Optional case ID for persistence
        force_refresh: If true, skip cache and re-analyze

    Returns:
        Wall analysis with insights, suggested links, and next actions
    """
    logger.info(
        f"Detective wall analyze: nodes={len(request.nodes)} edges={len(request.edges)} "
        f"cache={'skip' if force_refresh else 'use'}"
    )

    try:
        service = await get_wall_service()
        result = await service.analyze(
            request=request,
            case_id=case_id,
            force_refresh=force_refresh,
        )

        return result

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Detective wall analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-async")
async def analyze_wall_async(
    request: DetectiveWallAnalyzeRequest,
    case_id: str = Query("", description="Optional case ID for persistence"),
):
    """Submit async wall analysis job (for large walls).

    Useful when wall has many nodes (>50) to avoid timeout.
    Use /task-status endpoint to poll for results.

    Args:
        request: Wall analysis request
        case_id: Optional case ID

    Returns:
        Job ID for status polling
    """
    try:
        from junior.workers.celery_app import analyze_wall_async

        logger.info(f"📊 Submitting async wall analysis: case={case_id}")

        task = analyze_wall_async.delay(
            case_id=case_id,
            nodes_data=[n.model_dump() for n in request.nodes],
            edges_data=[e.model_dump() for e in request.edges],
            context=request.case_context or "",
        )

        return {
            "task_id": task.id,
            "status": "PENDING",
            "message": "Wall analysis submitted. Use /task-status to check progress.",
            "status_url": f"/api/v1/wall/task-status/{task.id}",
        }

    except Exception as e:
        logger.error(f"Failed to submit async job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Get status of async wall analysis job.

    Args:
        task_id: Task ID from /analyze-async response

    Returns:
        Task status, progress, and result (when done)
    """
    try:
        from junior.workers import get_task_status

        status_info = get_task_status(task_id)
        return status_info

    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task-cancel/{task_id}")
async def cancel_wall_analysis(task_id: str):
    """Cancel an in-progress async wall analysis.

    Args:
        task_id: Task ID to cancel

    Returns:
        Cancellation confirmation
    """
    try:
        from junior.workers import cancel_task

        logger.info(f"Cancelling task: {task_id}")
        cancel_task(task_id)

        return {
            "task_id": task_id,
            "status": "CANCELLED",
            "message": "Task cancelled successfully",
        }

    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/{snapshot_id}")
async def load_snapshot(snapshot_id: str):
    """Load a previously saved wall snapshot.

    Args:
        snapshot_id: ID of snapshot to load

    Returns:
        Snapshot data (nodes, edges, analysis)
    """
    try:
        service = await get_wall_service()
        snapshot = await service.load_snapshot(snapshot_id)

        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        return snapshot.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Load snapshot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache(_: str = Depends(auth.require_ops_admin)):
    """Clear all wall analysis cache (admin endpoint).

    Returns:
        Number of cache entries cleared
    """
    try:
        service = await get_wall_service()
        cleared = await service.clear_analysis_cache()
        return {"cleared": cleared, "message": f"Cleared {cleared} cache entries"}

    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
