"""Detective Wall endpoints

Provides an API to analyze the current detective wall canvas (nodes + edges)
using the DetectiveWallAgent.
"""

from fastapi import APIRouter, HTTPException

from junior.core import get_logger
from junior.core.exceptions import ConfigurationError
from junior.agents.detective_wall import DetectiveWallAgent
from junior.api.schemas import DetectiveWallAnalyzeRequest, DetectiveWallAnalyzeResponse

router = APIRouter()
logger = get_logger(__name__)

@router.post("/analyze", response_model=DetectiveWallAnalyzeResponse)
async def analyze_wall(request: DetectiveWallAnalyzeRequest):
    logger.info(f"Detective wall analyze: nodes={len(request.nodes)} edges={len(request.edges)}")

    try:
        agent = DetectiveWallAgent()
        result = await agent.analyze(
            case_context=request.case_context or "",
            nodes=[n.model_dump() for n in request.nodes],
            edges=[e.model_dump() for e in request.edges],
        )

        return DetectiveWallAnalyzeResponse(**result)

    except ConfigurationError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Detective wall analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
