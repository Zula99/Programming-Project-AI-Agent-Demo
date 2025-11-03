from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid # For generating unique IDs
import time # For simulating time-based operations
import httpx # For auto-proxy integration
import asyncio
import json
import logging
import sys
from typing import Dict, List, Optional
from io import StringIO
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Import WebSocket logging handler
from websocket_log_handler import setup_websocket_logging, websocket_connections, current_run_id

# Import task manager for background task cancellation
from task_manager import task_manager

# Import SmartMirrorAgent at module level to avoid first-request delay
sys.path.append(str(Path(__file__).parent / "crawl4ai-agent"))
from smart_mirror_agent import SmartMirrorAgent

# Initialize FastAPI app
app = FastAPI()

# Mount proxy as sub-application at /proxy-api (for API control endpoints)
from Proxy.proxy_server import app as proxy_app
app.mount("/proxy-api", proxy_app)
# Also mount at /proxy for actual proxied traffic
app.mount("/proxy", proxy_app)

# Include indexing API router (Phase 2+)
from API.indexing_routes import router as indexing_router
app.include_router(indexing_router)

# Configure CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionary stores Crawl4AI agent sessions
crawl4ai_sessions: Dict[str, Dict] = {}

# Set up WebSocket logging handler (broadcasts to frontend + OpenSearch)
setup_websocket_logging()


# Crawl4AI specific models
class Crawl4AIRequest(BaseModel):
    target_url: str
    max_pages: Optional[int] = None  # Optional limit for testing, defaults to intelligent stopping

class AgentResponseRequest(BaseModel):
    run_id: str
    response: str

class AgentLog(BaseModel):
    timestamp: str
    message: str
    type: str  # 'info', 'success', 'warning', 'error', 'question'


# --- API Endpoints ---

@app.get("/")
async def read_root():
    response = JSONResponse({"message": "Welcome to the Crawler Automation API!"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


# --- Crawl4AI Agent Endpoints ---

async def broadcast_to_websockets(run_id: str, message: dict):
    """Broadcast message to all WebSocket connections for a run_id"""
    if run_id in websocket_connections:
        dead_connections = []
        for ws in websocket_connections[run_id]:
            try:
                await ws.send_text(json.dumps(message))
            except:
                dead_connections.append(ws)

        # Remove dead connections
        for dead_ws in dead_connections:
            websocket_connections[run_id].remove(dead_ws)

async def add_agent_log(run_id: str, message: str, log_type: str = "info"):
    """Add a log entry and broadcast to WebSocket connections"""
    log_entry = {
        "timestamp": time.strftime("%H:%M:%S"),
        "message": message,
        "type": log_type
    }

    if run_id in crawl4ai_sessions:
        logs = crawl4ai_sessions[run_id]["logs"]
        logs.append(log_entry)

        # Circular buffer: keep only last 2000 entries
        if len(logs) > 2000:
            crawl4ai_sessions[run_id]["logs"] = logs[-2000:]

        # Broadcast to WebSocket connections
        await broadcast_to_websockets(run_id, {
            "type": "log",
            "log": log_entry
        })

async def update_agent_status(run_id: str, status: str, question: Optional[str] = None):
    """Update agent status and broadcast to WebSocket connections"""
    if run_id in crawl4ai_sessions:
        crawl4ai_sessions[run_id]["status"] = status
        if question:
            crawl4ai_sessions[run_id]["current_question"] = question

        await broadcast_to_websockets(run_id, {
            "type": "status",
            "status": status,
            "question": question
        })

async def update_progress(run_id: str, pages_crawled: int, total_pages: int, crawl_speed: float = 0,
                         ai_classifications: int = 0, cache_hits: int = 0):
    """Update crawl progress and broadcast to WebSocket connections"""
    if run_id in crawl4ai_sessions:
        progress = crawl4ai_sessions[run_id]["progress"]
        progress["pages_crawled"] = pages_crawled
        progress["total_pages"] = total_pages
        progress["pages_remaining"] = max(0, total_pages - pages_crawled)
        progress["percentage"] = (pages_crawled / total_pages * 100) if total_pages > 0 else 0
        progress["crawl_speed"] = crawl_speed
        progress["ai_classifications"] = ai_classifications
        progress["cache_hits"] = cache_hits
        # loaded_caches = initial sitemap caches + crawl cache hits
        progress["loaded_caches"] = cache_hits

        # Calculate estimated time remaining (in seconds)
        if crawl_speed > 0 and progress["pages_remaining"] > 0:
            progress["estimated_time_remaining"] = int((progress["pages_remaining"] / crawl_speed) * 60)
        else:
            progress["estimated_time_remaining"] = 0

        await broadcast_to_websockets(run_id, {
            "type": "progress",
            "progress": progress
        })

async def run_crawl4ai_agent_real(run_id: str, target_url: str):
    """
    Run the real Crawl4AI SmartMirrorAgent process
    """
    # Set run_id context for OpenSearch session-based logging
    current_run_id.set(run_id)

    logger = logging.getLogger("crawl4ai")
    logger.info(f"Starting real SmartMirrorAgent for: {target_url}")

    try:
        # Initialize session
        await update_agent_status(run_id, "running")
        await add_agent_log(run_id, " Crawl4AI SmartMirrorAgent initialized", "info")
        logger.info("SmartMirrorAgent session initialized successfully")

        # Create the agent instance (SmartMirrorAgent now imported at module level)
        agent = SmartMirrorAgent(memory_path="backend_agent_memory.json")
        await add_agent_log(run_id, " Starting site reconnaissance...", "info")
        logger.info("SmartMirrorAgent created, starting reconnaissance")

        # Create a progress callback to inject into the hybrid crawler
        async def progress_callback(pages_crawled: int, total_known: int, discovered_urls: int = 0, crawl_speed: float = 0,
                                   ai_classifications: int = 0, cache_hits: int = 0, current_url: str = None):
            """Real-time progress updates from hybrid crawler"""
            # Use max_pages as fixed total (if specified), otherwise use total_known
            max_pages = crawl4ai_sessions[run_id].get("max_pages")
            total_pages = max_pages if max_pages else total_known
            logger.info(f"Progress callback: crawled={pages_crawled}/{total_pages}, speed={crawl_speed:.1f} pages/min, cache_hits={cache_hits}")
            # Update current URL in session
            if current_url and run_id in crawl4ai_sessions:
                crawl4ai_sessions[run_id]["current_url"] = current_url
            await update_progress(run_id, pages_crawled, total_pages, crawl_speed, ai_classifications, cache_hits)

        # Inject progress callback into the agent's crawler if it's HybridCrawler
        if hasattr(agent, 'crawler'):
            agent.crawler.progress_callback = progress_callback

        # Run the actual SmartMirrorAgent
        await add_agent_log(run_id, f" Analyzing {target_url}", "info")
        logger.info(f"Starting SmartMirrorAgent process for {target_url}")

        # Execute the real agent process with run_id for stop checking
        success, metrics, output_path = await agent.process_url(target_url, run_id, max_pages=crawl4ai_sessions[run_id].get("max_pages"))

        # Report results
        if success:
            # Extract quality metrics
            overall_score = getattr(metrics, 'overall_score', 0) * 100 if metrics else 0

            await add_agent_log(run_id, " Crawl completed successfully!", "success")
            await add_agent_log(run_id, f" Quality Score: {overall_score:.1f}%", "success")

            if output_path:
                await add_agent_log(run_id, f" Output saved to: {output_path}", "info")
                logger.info(f"Crawl output saved to: {output_path}")

                # Store metadata in session
                crawl4ai_sessions[run_id]["output_path"] = output_path
                crawl4ai_sessions[run_id]["domain"] = urlparse(target_url).netloc
                crawl4ai_sessions[run_id]["completed_at"] = datetime.now().isoformat()
                crawl4ai_sessions[run_id]["quality_score"] = overall_score

                # Extract pages_crawled from metrics
                pages_crawled = getattr(metrics, 'pages_crawled', 0)
                if pages_crawled == 0:
                    # Try to get from progress if not in metrics
                    pages_crawled = crawl4ai_sessions[run_id]["progress"]["pages_crawled"]

                # Final fallback: count meta.json files in output directory
                if pages_crawled == 0 and output_path:
                    try:
                        meta_files = list(Path(output_path).rglob("meta.json"))
                        pages_crawled = len(meta_files)
                        logger.info(f"Counted {pages_crawled} pages from output directory")
                    except Exception as e:
                        logger.warning(f"Could not count pages from output directory: {e}")

                crawl4ai_sessions[run_id]["pages_crawled"] = pages_crawled

                # Save run metadata to file (persists to Docker volume)
                metadata_file = Path(output_path) / "run_metadata.json"
                metadata = {
                    "run_id": run_id,
                    "target_url": target_url,
                    "domain": urlparse(target_url).netloc,
                    "status": "completed",
                    "started_at": datetime.fromtimestamp(crawl4ai_sessions[run_id]["started_at"]).isoformat(),
                    "completed_at": datetime.now().isoformat(),
                    "pages_crawled": pages_crawled,
                    "quality_score": overall_score,
                    "output_path": output_path
                }

                try:
                    metadata_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    logger.info(f"Run metadata saved to: {metadata_file}")
                except Exception as e:
                    logger.error(f"Failed to save metadata file: {e}")

            # Final progress update with actual results from metrics
            pages_crawled = getattr(metrics, 'pages_crawled', 0)
            if pages_crawled > 0:
                await update_progress(run_id, pages_crawled, pages_crawled, 0)

            await update_agent_status(run_id, "completed")
            logger.info(f"SmartMirrorAgent completed successfully with {overall_score:.1f}% quality score")

        else:
            await add_agent_log(run_id, " Crawl failed", "error")
            await update_agent_status(run_id, "error")
            logger.error("SmartMirrorAgent process failed")

    except asyncio.CancelledError:
        # Task was cancelled by user
        await add_agent_log(run_id, " Crawl stopped by user", "warning")
        await update_agent_status(run_id, "stopped")
        logger.info(f"Crawl {run_id} cancelled by user request")
        raise  # Re-raise to properly handle task cancellation
    except ImportError as e:
        error_msg = f"SmartMirrorAgent not available: {str(e)}"
        await add_agent_log(run_id, f" {error_msg}", "error")
        await update_agent_status(run_id, "error")
        logger.error(error_msg)
    except Exception as e:
        error_msg = f"SmartMirrorAgent error: {str(e)}"
        await add_agent_log(run_id, f" {error_msg}", "error")
        await update_agent_status(run_id, "error")
        logger.error(error_msg)
    finally:
        # Clean up task from task manager
        task_manager.cleanup_task(run_id)

@app.options("/crawl4ai/start")
async def options_crawl4ai_start(response: Response):
    """Handle CORS preflight for crawl4ai start endpoint"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "3600"
    return {"message": "OK"}

@app.post("/crawl4ai/start")
async def start_crawl4ai(request: Crawl4AIRequest, background_tasks: BackgroundTasks, response: Response):
    """Start a new Crawl4AI agent session"""
    target_url = request.target_url
    run_id = str(uuid.uuid4())

    # Initialize session
    crawl4ai_sessions[run_id] = {
        "run_id": run_id,
        "target_url": target_url,
        "status": "pending",
        "started_at": time.time(),
        "logs": [],
        "current_question": None,
        "last_response": None,
        "current_url": None,  # Track current URL being crawled
        "max_pages": request.max_pages,  # Store max_pages for agent
        "progress": {
            "percentage": 0,
            "pages_crawled": 0,
            "pages_remaining": 0,
            "total_pages": 0,
            "estimated_time_remaining": 0,
            "crawl_speed": 0,  # pages per minute
            "ai_classifications": 0,  # AI classifications made during crawl
            "cache_hits": 0,  # Cache hits during crawl
            "loaded_caches": 0  # Total cached links (sitemap + crawl cache hits)
        }
    }

    # Initialize WebSocket connections list
    websocket_connections[run_id] = []

    # Create and register the background task
    task = asyncio.create_task(run_crawl4ai_agent_real(run_id, target_url))
    task_manager.register_task(run_id, task)

    # Add CORS headers directly to response
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.status_code = 202

    return {
        "run_id": run_id,
        "message": "Crawl4AI agent started",
        "status": "pending"
    }

@app.get("/crawl4ai/status/{run_id}")
async def get_crawl4ai_status(run_id: str):
    """Get the current status of a Crawl4AI agent session"""
    if run_id not in crawl4ai_sessions:
        raise HTTPException(status_code=404, detail="Crawl4AI session not found")

    session = crawl4ai_sessions[run_id]
    response = JSONResponse(content={
        "session": {
            "run_id": session["run_id"],
            "target_url": session["target_url"],
            "status": session["status"],
            "started_at": session["started_at"],
            "current_question": session.get("current_question")
        },
        "logs": session["logs"],
        "progress": session["progress"]
    })

    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response

@app.post("/crawl4ai/respond")
async def send_agent_response(request: AgentResponseRequest):
    """Send a response to the Crawl4AI agent"""
    if request.run_id not in crawl4ai_sessions:
        raise HTTPException(status_code=404, detail="Crawl4AI session not found")

    session = crawl4ai_sessions[request.run_id]

    if session["status"] != "waiting_for_input":
        raise HTTPException(status_code=400, detail="Agent is not waiting for input")

    # Store the response and change status
    session["last_response"] = request.response
    session["status"] = "running"
    session["current_question"] = None

    return JSONResponse(content={"message": "Response sent successfully"})

@app.post("/crawl4ai/stop/{run_id}")
async def stop_crawl4ai_agent(run_id: str):
    """Force stop a running Crawl4AI agent session immediately"""
    if run_id not in crawl4ai_sessions:
        raise HTTPException(status_code=404, detail="Crawl4AI session not found")

    session = crawl4ai_sessions[run_id]

    # Cancel the task
    logger = logging.getLogger(__name__)
    logger.info(f"FORCE STOP requested for crawl session {run_id}")

    # Immediately update status to stopped
    session["status"] = "stopped"

    # Calculate elapsed time
    elapsed_time = time.time() - session["started_at"]

    # Format elapsed time as MM:SS
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    elapsed_time_formatted = f"{minutes}m {seconds}s"

    # Collect metrics at stop time
    progress = session["progress"]
    stop_summary = {
        "pages_crawled": progress["pages_crawled"],
        "total_pages": progress["total_pages"],
        "percentage": progress["percentage"],
        "pages_remaining": progress["pages_remaining"],
        "elapsed_time": elapsed_time_formatted,
        "elapsed_seconds": int(elapsed_time),
        "cache_hits": progress["cache_hits"],
        "ai_classifications": progress["ai_classifications"],
        "current_url": session.get("current_url", "N/A"),
        "target_url": session["target_url"]
    }

    # Send log to frontend
    await add_agent_log(run_id, " FORCE STOP - Terminating crawl immediately", "warning")
    await add_agent_log(run_id, f" Stopped at: {stop_summary['pages_crawled']}/{stop_summary['total_pages']} pages ({stop_summary['percentage']:.1f}%)", "info")
    await update_agent_status(run_id, "stopped")

    # Cancel the background task (don't wait for response)
    await task_manager.cancel_task(run_id)

    return JSONResponse(content={
        "message": "Crawl force stopped",
        "run_id": run_id,
        "status": "stopped",
        "summary": stop_summary
    })

@app.websocket("/crawl4ai/ws/{run_id}")
async def crawl4ai_websocket(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for live Crawl4AI agent updates"""
    await websocket.accept()

    # Add to connections list
    if run_id not in websocket_connections:
        websocket_connections[run_id] = []
    websocket_connections[run_id].append(websocket)

    try:
        # Send existing logs if session exists
        if run_id in crawl4ai_sessions:
            session = crawl4ai_sessions[run_id]
            for log in session["logs"]:
                await websocket.send_text(json.dumps({
                    "type": "log",
                    "log": log
                }))

            # Send current status
            await websocket.send_text(json.dumps({
                "type": "status",
                "status": session["status"],
                "question": session.get("current_question")
            }))

            # Send current progress
            await websocket.send_text(json.dumps({
                "type": "progress",
                "progress": session["progress"]
            }))

        # Keep connection alive
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        # Remove from connections list
        if run_id in websocket_connections:
            websocket_connections[run_id].remove(websocket)

# --- Server Startup ---
if __name__ == "__main__":
    import uvicorn
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Agent Demo Factory Backend on port 8000...")
    logger.info("Crawl4AI endpoints available at:")
    logger.info("  POST /crawl4ai/start")
    logger.info("  GET /crawl4ai/status/{run_id}")
    logger.info("  WebSocket /crawl4ai/ws/{run_id}")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
