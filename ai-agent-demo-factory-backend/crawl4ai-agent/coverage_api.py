"""
Coverage API - Frontend-facing endpoints for real-time crawl monitoring

Clean REST API + WebSocket endpoints for frontend integration.
All crawl monitoring logic centralized here - frontend devs don't need
to understand crawler internals.

US-53: Real-time Coverage Monitoring & Visualization
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from dashboard_metrics import (
    CoverageSnapshot, CoverageCalculator, CrawlPhase,
    create_coverage_calculator, get_coverage_calculator, 
    remove_coverage_calculator, get_all_active_runs
)
from websocket_manager import websocket_manager, cleanup_websocket_connections


# Pydantic models for API requests/responses
class CrawlStartRequest(BaseModel):
    """Request to start a new crawl with coverage monitoring"""
    start_url: str
    max_pages: Optional[int] = None
    run_id: Optional[str] = None  # Auto-generated if not provided


class CrawlStatusResponse(BaseModel):
    """Current crawl status response"""
    run_id: str
    status: str
    phase: str
    coverage_percentage: float
    pages_crawled: int
    total_known_urls: int
    estimated_time_remaining: Optional[int]
    quality_plateau_detected: bool


class CrawlSummaryResponse(BaseModel):
    """Final crawl summary response"""
    run_id: str
    success: bool
    final_coverage_percentage: float
    total_pages_crawled: int
    total_urls_discovered: int
    average_quality_score: float
    total_execution_time: float
    stop_reason: Optional[str]


# Initialize FastAPI app (this would be integrated into main app)
app = FastAPI(title="Coverage Monitoring API", version="1.0.0")
logger = logging.getLogger(__name__)


@app.get("/coverage/{run_id}", response_model=Dict[str, Any])
async def get_coverage_status(run_id: str):
    """
    Get current coverage status for a running crawl
    
    Returns real-time metrics including:
    - Coverage percentage (dynamic as URLs are discovered)
    - Pages crawled vs total known URLs
    - Quality trends and velocity
    - Estimated time remaining
    """
    calculator = get_coverage_calculator(run_id)
    if not calculator:
        raise HTTPException(status_code=404, detail=f"Run ID {run_id} not found")
    
    snapshot = calculator.get_current_snapshot()
    
    return {
        "run_id": run_id,
        "timestamp": snapshot.timestamp,
        "status": "active" if snapshot.phase in [CrawlPhase.CRAWLING, CrawlPhase.SITEMAP_ANALYSIS] else snapshot.phase.value,
        "phase": snapshot.phase.value,
        "coverage": {
            "percentage": round(snapshot.coverage_percentage, 2),
            "pages_crawled": snapshot.pages_crawled,
            "total_known_urls": snapshot.total_known_urls,
            "initial_sitemap_urls": snapshot.initial_sitemap_urls,
            "discovered_urls": snapshot.discovered_urls
        },
        "quality": {
            "recent_score": round(snapshot.recent_quality_score, 3),
            "trend": snapshot.overall_quality_trend,
            "plateau_detected": snapshot.quality_plateau_detected
        },
        "performance": {
            "crawl_velocity": round(snapshot.crawl_velocity, 2),
            "estimated_time_remaining": snapshot.estimated_time_remaining
        },
        "current_activity": {
            "current_url": snapshot.current_url,
            "stop_reason": snapshot.stop_reason
        }
    }


@app.get("/coverage/{run_id}/summary", response_model=Dict[str, Any])
async def get_crawl_summary(run_id: str):
    """
    Get comprehensive crawl summary and final statistics
    
    Best used after crawl completion, but can be called during
    crawling for intermediate statistics.
    """
    calculator = get_coverage_calculator(run_id)
    if not calculator:
        raise HTTPException(status_code=404, detail=f"Run ID {run_id} not found")
    
    summary = calculator.get_summary_stats()
    
    return {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "completion_status": {
            "final_phase": summary['final_phase'],
            "coverage_achieved": round(summary['final_coverage_percentage'], 2),
            "quality_plateau_detected": summary['quality_plateau_detected'],
            "stop_reason": summary['stop_reason']
        },
        "crawl_results": {
            "pages_crawled": summary['total_pages_crawled'],
            "pages_failed": summary['total_pages_failed'],
            "urls_discovered": summary['total_urls_discovered'],
            "initial_sitemap_urls": summary['initial_sitemap_urls'],
            "discovered_during_crawl": summary['discovered_during_crawl']
        },
        "quality_metrics": {
            "average_quality_score": round(summary['average_quality_score'], 3),
            "quality_trend": summary['quality_trend']
        },
        "performance_metrics": {
            "total_execution_time": round(summary['total_execution_time'], 2),
            "pure_crawl_time": round(summary['pure_crawl_time'], 2),
            "average_crawl_velocity": round(summary['average_crawl_velocity'], 2)
        }
    }


@app.get("/active-runs", response_model=List[Dict[str, Any]])
async def get_active_runs():
    """
    Get list of all currently active crawl runs
    
    Useful for dashboard overview of all running crawls
    """
    active_runs = get_all_active_runs()
    websocket_connections = websocket_manager.get_all_active_runs()
    
    result = []
    for run_id in active_runs:
        calculator = get_coverage_calculator(run_id)
        if calculator:
            snapshot = calculator.get_current_snapshot()
            result.append({
                "run_id": run_id,
                "phase": snapshot.phase.value,
                "coverage_percentage": round(snapshot.coverage_percentage, 2),
                "pages_crawled": snapshot.pages_crawled,
                "websocket_connections": websocket_connections.get(run_id, 0),
                "last_update": snapshot.timestamp
            })
    
    return result


@app.delete("/coverage/{run_id}")
async def cleanup_crawl_run(run_id: str, background_tasks: BackgroundTasks):
    """
    Clean up crawl run data and close WebSocket connections
    
    Should be called when crawl is complete and no longer needed
    """
    calculator = get_coverage_calculator(run_id)
    if not calculator:
        raise HTTPException(status_code=404, detail=f"Run ID {run_id} not found")
    
    # Schedule background cleanup
    background_tasks.add_task(cleanup_websocket_connections, run_id)
    background_tasks.add_task(remove_coverage_calculator, run_id)
    
    return {"message": f"Cleanup scheduled for run ID {run_id}"}


@app.websocket("/ws/coverage/{run_id}")
async def coverage_websocket(websocket: WebSocket, run_id: str):
    """
    WebSocket endpoint for real-time coverage updates
    
    Clients connect here to receive live crawling progress:
    - Coverage percentage updates
    - Quality trend changes  
    - Phase transitions
    - Quality plateau alerts
    - Crawl completion notifications
    """
    await websocket_manager.connect(websocket, run_id)
    
    try:
        # Keep connection alive and handle any client messages
        while True:
            # Wait for client messages (ping, requests, etc.)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client requests
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "status":
                    # Send current status on request
                    calculator = get_coverage_calculator(run_id)
                    if calculator:
                        snapshot = calculator.get_current_snapshot()
                        await websocket_manager.broadcast_coverage_update(run_id, snapshot)
                
            except asyncio.TimeoutError:
                # Send periodic heartbeat
                await websocket.send_text('{"type": "heartbeat"}')
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, run_id)
        logger.info(f"WebSocket disconnected for run_id: {run_id}")
    except Exception as e:
        logger.error(f"WebSocket error for run_id {run_id}: {e}")
        websocket_manager.disconnect(websocket, run_id)


# Helper functions for crawler integration
def generate_run_id() -> str:
    """Generate unique run ID for new crawl"""
    return f"crawl_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"


async def initialize_coverage_tracking(run_id: str, start_url: str, sitemap_urls: Optional[List[str]] = None) -> CoverageCalculator:
    """
    Initialize coverage tracking for new crawl
    
    To be called from crawler when starting new crawl job
    """
    calculator = create_coverage_calculator(run_id)
    calculator.set_phase(CrawlPhase.INITIALIZING)
    
    if sitemap_urls:
        calculator.initialize_sitemap_urls(sitemap_urls)
        logger.info(f"Initialized coverage tracking for {run_id} with {len(sitemap_urls)} sitemap URLs")
    else:
        logger.info(f"Initialized coverage tracking for {run_id} with progressive discovery")
    
    # Notify WebSocket clients
    await websocket_manager.broadcast_crawl_event(run_id, 'crawl_initialized', {
        'start_url': start_url,
        'has_sitemap': bool(sitemap_urls),
        'initial_url_count': len(sitemap_urls) if sitemap_urls else 1
    })
    
    return calculator


async def finalize_coverage_tracking(run_id: str, success: bool, final_stats: Optional[Dict] = None):
    """
    Finalize coverage tracking when crawl completes
    
    To be called from crawler when crawl job finishes
    """
    calculator = get_coverage_calculator(run_id)
    if calculator:
        calculator.set_phase(CrawlPhase.COMPLETED if success else CrawlPhase.FAILED)
        
        # Get final summary
        summary = calculator.get_summary_stats()
        if final_stats:
            summary.update(final_stats)
        
        # Notify WebSocket clients
        await websocket_manager.send_crawl_completion(run_id, summary)
        
        logger.info(f"Finalized coverage tracking for {run_id}: {summary['final_coverage_percentage']:.1f}% coverage, {summary['total_pages_crawled']} pages")
        
        return summary
    
    return None


# Health check endpoint
@app.get("/health")
async def health_check():
    """API health check"""
    active_runs = len(get_all_active_runs())
    websocket_connections = sum(websocket_manager.get_all_active_runs().values())
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_crawls": active_runs,
        "websocket_connections": websocket_connections
    }