"""
Indexing API Routes - Manual indexing and proxy control endpoints

Provides REST API endpoints for:
- Listing completed crawls
- Manual OpenSearch indexing (Phase 3)
- Proxy control (Phase 4)

Part of PLAN.md phased implementation for Proxy & Index Control System.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
from pathlib import Path
import logging

# Add Utility to path for crawl_storage
sys.path.insert(0, str(Path(__file__).parent.parent / "Utility"))
from crawl_storage import list_all_crawls, get_crawl_by_run_id

# Initialize router
router = APIRouter(prefix="/api", tags=["indexing"])
logger = logging.getLogger(__name__)


# ============================================================================
# PHASE 2: Crawl Discovery Endpoints
# ============================================================================

@router.get("/crawls/completed")
async def get_completed_crawls():
    """
    List all completed crawls from filesystem + active sessions

    Returns list of crawl metadata including run_id, domain, status,
    pages_crawled, quality_score, and output_path.

    This endpoint combines:
    - Completed crawls from filesystem (run_metadata.json files)
    - Active/running crawls from in-memory sessions

    Phase: 2 (Crawl Discovery System)
    """
    try:
        # Import sessions inside function to avoid circular dependency
        from main import crawl4ai_sessions

        # Get all crawls (filesystem + sessions)
        crawls = list_all_crawls(active_sessions=crawl4ai_sessions)

        logger.info(f"Returning {len(crawls)} crawls from /api/crawls/completed")

        return {
            "crawls": crawls,
            "count": len(crawls)
        }

    except Exception as e:
        logger.error(f"Failed to list completed crawls: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list crawls: {str(e)}"
        )


@router.get("/crawls/{run_id}")
async def get_crawl_details(run_id: str):
    """
    Get detailed metadata for a specific crawl

    Args:
        run_id: Unique run identifier

    Returns:
        Crawl metadata dictionary

    Phase: 2 (Crawl Discovery System)
    """
    try:
        # Check active sessions first
        from main import crawl4ai_sessions

        if run_id in crawl4ai_sessions:
            session = crawl4ai_sessions[run_id]
            return {
                "run_id": run_id,
                "target_url": session["target_url"],
                "domain": session.get("domain", ""),
                "status": session["status"],
                "started_at": session.get("started_at", ""),
                "completed_at": session.get("completed_at"),
                "pages_crawled": session.get("pages_crawled", 0),
                "quality_score": session.get("quality_score"),
                "output_path": session.get("output_path", "")
            }

        # Check filesystem
        metadata = get_crawl_by_run_id(run_id)
        if metadata:
            return metadata

        raise HTTPException(status_code=404, detail=f"Crawl {run_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get crawl details for {run_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get crawl details: {str(e)}"
        )


# ============================================================================
# PHASE 3: Manual Indexing Endpoints (Placeholder)
# ============================================================================

# TODO: Add in Phase 3
# @router.post("/opensearch/index")
# async def index_crawl_data(request: IndexRequest):
#     """Index crawl data to OpenSearch with progress logging"""
#     pass

# @router.get("/opensearch/indexes")
# async def get_opensearch_indexes():
#     """List all OpenSearch demo indexes"""
#     pass


# ============================================================================
# PHASE 4: Proxy Control Endpoints (Placeholder)
# ============================================================================

# TODO: Add in Phase 4
# @router.post("/proxy/launch")
# async def launch_proxy(request: ProxyLaunchRequest):
#     """Launch proxy server with target URL and index"""
#     pass

# @router.post("/proxy/stop")
# async def stop_proxy():
#     """Stop proxy server"""
#     pass

# @router.get("/proxy/status")
# async def get_proxy_status():
#     """Get proxy server status"""
#     pass
