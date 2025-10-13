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
import httpx
from urllib.parse import urlparse

# Add Utility to path for crawl_storage
sys.path.insert(0, str(Path(__file__).parent.parent / "Utility"))
from crawl_storage import list_all_crawls, get_crawl_by_run_id

# Initialize router
router = APIRouter(prefix="/api", tags=["indexing"])
logger = logging.getLogger(__name__)

# Proxy is mounted as sub-app at /proxy-api (same port as main app)
PROXY_SERVER_URL = "http://localhost:8000/proxy-api"


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
# PHASE 3: Manual Indexing Endpoints
# ============================================================================

# Import OpenSearch integration
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "Utility"))
from opensearch_integration import Crawl4AIOpenSearchIntegration, OpenSearchConfig
from websocket_log_handler import current_run_id


class IndexRequest(BaseModel):
    run_id: str
    output_path: str
    domain: str


@router.post("/opensearch/index")
async def index_crawl_data(request: IndexRequest):
    """
    Index crawl data to OpenSearch with progress logging

    Args:
        request: IndexRequest with run_id, output_path, and domain

    Returns:
        Indexing result with stats

    Phase: 3 (Manual Indexing)
    """
    try:
        # Set logging context for WebSocket (shows in backend logs)
        current_run_id.set(request.run_id)
        index_logger = logging.getLogger("opensearch_indexing")

        # Create index name: demo-{domain}-{run_id}
        domain_clean = request.domain.replace(".", "_")
        index_name = f"demo-{domain_clean}-{request.run_id}"

        index_logger.info(f"Starting OpenSearch indexing: {index_name}")
        index_logger.info(f"Source: {request.output_path}")

        # Initialize OpenSearch
        config = OpenSearchConfig(host="opensearch", port=9200, scheme="http")
        opensearch = Crawl4AIOpenSearchIntegration(config)

        # Check if index already exists
        if opensearch.index_exists(index_name):
            index_logger.warning(f"Index {index_name} already exists - will append data")

        # Index data (index_crawl4ai_data logs progress automatically)
        stats = opensearch.index_crawl4ai_data(
            crawl_output_dir=request.output_path,
            index_name=index_name,
            batch_size=100
        )

        index_logger.info(f"Indexing complete!")
        index_logger.info(f"  Documents indexed: {stats.get('documents_indexed', 0)}")
        index_logger.info(f"  Duration: {stats.get('duration', 0):.2f}s")
        index_logger.info(f"  Errors: {stats.get('errors', 0)}")

        return {
            "index_name": index_name,
            "stats": stats,
            "message": f"Successfully indexed {stats.get('documents_indexed', 0)} documents"
        }

    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.get("/opensearch/indexes")
async def get_opensearch_indexes():
    """
    List all OpenSearch demo indexes

    Returns:
        List of all demo-* indexes with metadata

    Phase: 3 (Manual Indexing)
    """
    try:
        config = OpenSearchConfig(host="opensearch", port=9200, scheme="http")
        opensearch = Crawl4AIOpenSearchIntegration(config)
        indexes = opensearch.get_all_demo_indexes()

        return {
            "indexes": indexes,
            "count": len(indexes)
        }

    except Exception as e:
        logger.error(f"Failed to list OpenSearch indexes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list indexes: {str(e)}"
        )


# ============================================================================
# PHASE 4: Proxy Control Endpoints
# ============================================================================

class ProxyLaunchRequest(BaseModel):
    target_url: str
    run_id: str


@router.post("/proxy/launch")
async def launch_proxy(request: ProxyLaunchRequest):
    """
    Launch proxy server with target URL and index

    Args:
        request: ProxyLaunchRequest with target_url and run_id

    Returns:
        Proxy launch confirmation with proxy URL

    Phase: 4 (Proxy Control)
    """
    try:
        # Generate index name from run_id (matches indexing naming)
        domain = urlparse(request.target_url).netloc
        domain_clean = domain.replace(".", "_")
        index_name = f"demo-{domain_clean}-{request.run_id}"

        # Call proxy_server's /auto-configure endpoint
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{PROXY_SERVER_URL}/auto-configure",
                json={
                    "target_url": request.target_url,
                    "run_id": request.run_id,
                    "enabled": True
                }
            )
            response.raise_for_status()

        proxy_logger = logging.getLogger("proxy")
        proxy_logger.info(f"Proxy launched: {request.target_url} -> {index_name}")

        return {
            "message": "Proxy launched successfully",
            "proxy_url": "http://localhost:8000/proxy/",
            "target_url": request.target_url,
            "index_name": index_name
        }

    except httpx.HTTPError as e:
        logger.error(f"Proxy server unavailable: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Proxy server unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to launch proxy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to launch proxy: {str(e)}")


@router.post("/proxy/stop")
async def stop_proxy():
    """
    Stop proxy server

    Returns:
        Stop confirmation message

    Phase: 4 (Proxy Control)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{PROXY_SERVER_URL}/auto-configure",
                json={"target_url": "", "enabled": False}
            )
            response.raise_for_status()

        proxy_logger = logging.getLogger("proxy")
        proxy_logger.info("Proxy stopped")

        return {"message": "Proxy stopped"}

    except httpx.HTTPError as e:
        logger.error(f"Failed to stop proxy: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Proxy server unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to stop proxy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop proxy: {str(e)}")


@router.get("/proxy/status")
async def get_proxy_status():
    """
    Get proxy server status

    Returns:
        Proxy configuration and status

    Phase: 4 (Proxy Control)
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PROXY_SERVER_URL}/config")
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError:
        return {
            "enabled": False,
            "target_url": None,
            "message": "Proxy server not running"
        }
    except Exception as e:
        logger.error(f"Failed to get proxy status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get proxy status: {str(e)}")
