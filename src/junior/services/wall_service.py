"""
Detective Wall Service

Provides:
- Cached wall analysis with Redis
- Wall snapshot persistence
- Version management
- Provenance tracking
- Proactive suggestion integration
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from junior.core import get_logger, settings
from junior.db import get_redis_client
from junior.agents.detective_wall import DetectiveWallAgent
from junior.api.schemas import (
    DetectiveWallAnalyzeRequest,
    DetectiveWallAnalyzeResponse,
    DetectiveWallNode,
)

logger = get_logger(__name__)


class WallSnapshot:
    """Represents a saved state of the detective wall."""

    def __init__(
        self,
        wall_id: str,
        case_id: str,
        nodes: list[dict],
        edges: list[dict],
        analysis: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ):
        self.wall_id = wall_id
        self.case_id = case_id
        self.nodes = nodes
        self.edges = edges
        self.analysis = analysis or {}
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()
        self.version = 1

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "wall_id": self.wall_id,
            "case_id": self.case_id,
            "nodes": self.nodes,
            "edges": self.edges,
            "analysis": self.analysis,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WallSnapshot":
        """Create from dictionary."""
        snapshot = cls(
            wall_id=data.get("wall_id", ""),
            case_id=data.get("case_id", ""),
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
            analysis=data.get("analysis"),
            metadata=data.get("metadata"),
        )
        snapshot.created_at = data.get("created_at", snapshot.created_at)
        snapshot.version = data.get("version", 1)
        return snapshot


class DetectiveWallService:
    """Service for wall analysis, caching, and persistence."""

    def __init__(self):
        self.agent = DetectiveWallAgent()
        self.redis = None

    async def initialize(self):
        """Initialize service with Redis connection."""
        try:
            self.redis = await get_redis_client()
            logger.info("✅ Wall service initialized")
        except Exception as e:
            logger.warning(f"⚠️  Wall service Redis init skipped: {e}")

    async def analyze(
        self,
        request: DetectiveWallAnalyzeRequest,
        case_id: str = "",
        force_refresh: bool = False,
    ) -> DetectiveWallAnalyzeResponse:
        """
        Analyze the detective wall with caching.

        Args:
            request: Wall analysis request (nodes, edges, context)
            case_id: Case ID for persistence (optional)
            force_refresh: Skip cache and re-analyze

        Returns:
            Wall analysis response with insights and suggestions
        """
        # Generate cache key
        cache_key = self._generate_analysis_cache_key(request)

        # Try to get from cache
        if not force_refresh and self.redis:
            try:
                cached = await self.redis.get(
                    cache_key,
                    namespace="wall:analysis",
                    default=None,
                )
                if cached:
                    logger.info(f"✅ Wall analysis cache HIT: {cache_key[:20]}...")
                    cached_response = DetectiveWallAnalyzeResponse(**cached)
                    cached_response.cache_status = "hit"
                    if not cached_response.analysis_timestamp:
                        cached_response.analysis_timestamp = datetime.utcnow().isoformat()
                    return cached_response
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")

        logger.info(f"📊 Analyzing wall: {len(request.nodes)} nodes, {len(request.edges)} edges")

        try:
            # Run wall analysis
            analysis_result = await self.agent.analyze(
                case_context=request.case_context or "",
                nodes=[n.model_dump() for n in request.nodes],
                edges=[e.model_dump() for e in request.edges],
            )

            # Get proactive suggestions
            proactive_suggestions = await self._get_proactive_suggestions(
                request=request,
                analysis=analysis_result,
                case_id=case_id,
            )

            # Merge proactive suggestions into next_actions
            all_actions = analysis_result.get("next_actions", [])
            if proactive_suggestions:
                all_actions.extend(proactive_suggestions)

            # Build response
            cache_status = "fresh" if force_refresh else "miss"
            response_data = {
                **analysis_result,
                "next_actions": all_actions,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "cache_status": cache_status,
                "proactive_suggestions_count": len(proactive_suggestions),
            }
            snapshot_id = None

            # Save snapshot if case_id provided
            if case_id:
                try:
                    snapshot_id = await self.save_snapshot(
                        case_id=case_id,
                        nodes=[n.model_dump() for n in request.nodes],
                        edges=[e.model_dump() for e in request.edges],
                        analysis=response_data,
                    )
                except Exception as e:
                    logger.warning(f"Failed to save snapshot: {e}")

            response_data["snapshot_id"] = snapshot_id
            response = DetectiveWallAnalyzeResponse(**response_data)

            # Cache the result
            if self.redis:
                try:
                    await self.redis.set(
                        cache_key,
                        response.model_dump(),
                        ttl=settings.redis_wall_cache_ttl,
                        namespace="wall:analysis",
                    )
                    logger.debug(f"Cached wall analysis: {cache_key[:20]}...")
                except Exception as e:
                    logger.warning(f"Failed to cache analysis: {e}")

            return response

        except Exception as e:
            logger.error(f"Wall analysis error: {e}", exc_info=True)
            raise

    async def _get_proactive_suggestions(
        self,
        request: DetectiveWallAnalyzeRequest,
        analysis: dict,
        case_id: str = "",
    ) -> list[str]:
        """Get proactive suggestions to merge into analysis."""
        try:
            # Cache key for proactive suggestions
            cache_key = f"proactive:{case_id}" if case_id else "proactive:global"

            # Try cache first
            if self.redis:
                try:
                    cached = await self.redis.get(
                        cache_key,
                        namespace="wall:suggestions",
                        default=None,
                    )
                    if cached:
                        logger.debug(f"Proactive suggestions cache HIT: {cache_key}")
                        return cached if isinstance(cached, list) else []
                except Exception:
                    pass

            # Get fresh suggestions (if service is available)
            try:
                from junior.services.proactive_assistant import get_proactive_service

                service = get_proactive_service()
                suggestion_text = await service.analyze_and_suggest(
                    conversation_history=[],  # Empty for wall context
                    detective_wall_nodes=[n.model_dump() for n in request.nodes],
                    recent_documents=[],  # Can be enhanced to include actual documents
                )

                suggestions_list = []
                if suggestion_text and suggestion_text != "NO_SUGGESTION":
                    # Split suggestion into actionable items
                    suggestions_list = [s.strip() for s in suggestion_text.split("\n") if s.strip()]

                # Cache suggestions. Cache empty list briefly to avoid repeated retries on upstream limits.
                if self.redis:
                    try:
                        suggestion_ttl = settings.redis_suggestion_cache_ttl if suggestions_list else 120
                        await self.redis.set(
                            cache_key,
                            suggestions_list,
                            ttl=suggestion_ttl,
                            namespace="wall:suggestions",
                        )
                    except Exception:
                        pass

                return suggestions_list[:5]  # Return top 5 suggestions
            except Exception as e:
                logger.debug(f"Proactive suggestions skipped: {e}")

            return []
        except Exception as e:
            logger.warning(f"Error getting proactive suggestions: {e}")
            return []

    async def save_snapshot(
        self,
        case_id: str,
        nodes: list[dict],
        edges: list[dict],
        analysis: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Save a wall snapshot for later retrieval.

        Args:
            case_id: Case ID
            nodes: Wall nodes
            edges: Wall edges (connections)
            analysis: Analysis result
            metadata: Additional metadata

        Returns:
            Snapshot ID
        """
        snapshot_id = str(uuid4())
        snapshot = WallSnapshot(
            wall_id=snapshot_id,
            case_id=case_id,
            nodes=nodes,
            edges=edges,
            analysis=analysis,
            metadata=metadata or {"saved_at": datetime.utcnow().isoformat()},
        )

        # Save to Redis for quick access
        if self.redis:
            try:
                cache_key = f"snapshot:{snapshot_id}"
                await self.redis.set(
                    cache_key,
                    snapshot.to_dict(),
                    ttl=None,  # Keep indefinitely
                    namespace="wall:snapshots",
                )
                logger.info(f"✅ Snapshot saved: {snapshot_id}")
            except Exception as e:
                logger.error(f"Failed to save snapshot to Redis: {e}")

        # TODO: Also save to Supabase for permanent storage
        # This would involve:
        # 1. Creating a wall_snapshots table in Supabase
        # 2. Storing snapshot JSON with metadata
        # 3. Indexing by case_id for retrieval

        return snapshot_id

    async def load_snapshot(self, snapshot_id: str) -> Optional[WallSnapshot]:
        """Load a saved wall snapshot."""
        if not self.redis:
            return None

        try:
            cache_key = f"snapshot:{snapshot_id}"
            snapshot_data = await self.redis.get(
                cache_key,
                namespace="wall:snapshots",
                default=None,
            )
            if snapshot_data:
                logger.info(f"✅ Snapshot loaded: {snapshot_id}")
                return WallSnapshot.from_dict(snapshot_data)
            else:
                logger.warning(f"Snapshot not found: {snapshot_id}")
                return None
        except Exception as e:
            logger.error(f"Failed to load snapshot: {e}")
            return None

    async def list_snapshots(self, case_id: str) -> list[dict]:
        """List all snapshots for a case."""
        # TODO: Implement pagination and filtering
        # For now, return empty list
        logger.debug(f"Listing snapshots for case: {case_id}")
        return []

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a saved snapshot."""
        if not self.redis:
            return False

        try:
            cache_key = f"snapshot:{snapshot_id}"
            deleted = await self.redis.delete(
                cache_key,
                namespace="wall:snapshots",
            )
            if deleted:
                logger.info(f"✅ Snapshot deleted: {snapshot_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete snapshot: {e}")
            return False

    async def clear_analysis_cache(self) -> int:
        """Clear all wall analysis cache."""
        if not self.redis:
            return 0

        try:
            cleared = await self.redis.clear_namespace(namespace="wall:analysis")
            logger.info(f"✅ Cleared {cleared} analysis cache entries")
            return cleared
        except Exception as e:
            logger.error(f"Failed to clear analysis cache: {e}")
            return 0

    @staticmethod
    def _generate_analysis_cache_key(request: DetectiveWallAnalyzeRequest) -> str:
        """Generate a unique cache key for wall analysis request."""
        # Create a deterministic hash based on nodes and edges
        request_dict = {
            "nodes": [n.model_dump() for n in request.nodes],
            "edges": [e.model_dump() for e in request.edges],
            "context": request.case_context or "",
        }
        request_json = json.dumps(request_dict, sort_keys=True)
        key_hash = hashlib.md5(request_json.encode()).hexdigest()
        return f"analysis:{key_hash}"


# Global instance
_service: Optional[DetectiveWallService] = None


async def get_wall_service() -> DetectiveWallService:
    """Get or create wall service instance."""
    global _service
    if _service is None:
        _service = DetectiveWallService()
        await _service.initialize()
    return _service
