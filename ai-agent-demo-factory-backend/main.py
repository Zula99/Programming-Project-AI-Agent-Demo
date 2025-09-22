from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid # For generating unique IDs
import time # For simulating time-based operations
import threading # For running the simulation in a separate thread
import httpx # For auto-proxy integration
import asyncio
import json
from typing import Dict, List, Optional

# Initialize FastAPI app
app = FastAPI()

# Configure CORS 
# Adjust the 'origins' list to include the actual URL(s) where your frontend is hosted.
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5000" # Explicitly allow self, if needed for some tests
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],    # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],    # Allow all headers
)


# Dictionary stores crawl statuses and simulated results in memory.
crawl_jobs = {}

# Dictionary stores Crawl4AI agent sessions and their WebSocket connections
crawl4ai_sessions: Dict[str, Dict] = {}
websocket_connections: Dict[str, List[WebSocket]] = {}

# Pydantic model for validating the request body when starting a crawl.
# FastAPI uses this to automatically validate incoming JSON data.
class CrawlRequest(BaseModel):
    target_url: str

# Pydantic model for the structure of a single page result.
# Used for documenting and validating the 'results' array.
class PageRow(BaseModel):
    id: str
    path: str
    title: str
    type: str # e.g., "html", "pdf", "doc"
    size: int # size in bytes

# Crawl4AI specific models
class Crawl4AIRequest(BaseModel):
    target_url: str

class AgentResponseRequest(BaseModel):
    run_id: str
    response: str

class AgentLog(BaseModel):
    timestamp: str
    message: str
    type: str  # 'info', 'success', 'warning', 'error', 'question'

# --- Helper Function: Auto-configure proxy after crawl ---
async def auto_configure_proxy(run_id: str, target_url: str):
    """Auto-configure proxy server when crawl completes"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:8001/auto-configure", json={
                "target_url": target_url,
                "run_id": run_id,
                "enabled": True
            })
        print(f"[{run_id}] Auto-proxy configured for {target_url}")
    except Exception as e:
        print(f"[{run_id}] Failed to configure auto-proxy: {e}")

# --- Helper Function: Simulates the Norconex Crawler ---
def run_norconex_crawler_simulation(run_id: str, target_url: str):
    """
    This function simulates the asynchronous web crawling process.
    In a production setup, this is where you would integrate with the
    actual Norconex crawler (e.g., by calling its CLI or API).

    It updates the 'crawl_jobs' dictionary to reflect the current status
    and progressively adds simulated page results.
    """
    print(f"[{run_id}] Simulating crawl for: {target_url}")
    # Update job status to 'running' and reset progress
    crawl_jobs[run_id]['status'] = 'running'
    crawl_jobs[run_id]['progress'] = 0

    # Define a list of mock pages that will be crawled
    mock_pages = [
        {"id": "1", "path": "/", "title": "Home Page", "type": "html", "size": 18322},
        {"id": "2", "path": "/products", "title": "Our Products", "type": "html", "size": 25101},
        {"id": "3", "path": "/contact", "title": "Contact Us", "type": "html", "size": 19552},
        {"id": "4", "path": "/about-us", "title": "About Our Company", "type": "html", "size": 30000},
        {"id": "5", "path": "/services", "title": "Our Services", "type": "html", "size": 150000},
        {"id": "6", "path": "/blog/latest", "title": "Latest Blog Post", "type": "html", "size": 22000},
        {"id": "7", "path": "/privacy-policy.pdf", "title": "Privacy Policy", "type": "pdf", "size": 12000},
        {"id": "8", "path": "/terms-of-service", "title": "Terms and Conditions", "type": "html", "size": 28000},
        {"id": "9", "path": "/careers", "title": "Careers at Our Company", "type": "html", "size": 17000},
        {"id": "10", "path": "/faq", "title": "Frequently Asked Questions", "type": "html", "size": 80000},
    ]

    # Loop through mock pages to simulate crawling progress
    for i, page in enumerate(mock_pages):
        time.sleep(1) # Pause for 1 second to simulate work
        # Calculate progress percentage
        current_progress = int(((i + 1) / len(mock_pages)) * 100)
        crawl_jobs[run_id]['progress'] = current_progress
        # Add the "crawled" page to the results list for this job
        crawl_jobs[run_id]['results'].append(page)
        print(f"[{run_id}] Progress: {crawl_jobs[run_id]['progress']}% - Added {page['path']}")

    # After all pages are "crawled", set the final status
    # This example includes a simple error simulation based on the URL
    if "error" in target_url:
        crawl_jobs[run_id]['status'] = 'failed'
        crawl_jobs[run_id]['error_message'] = 'Simulated crawl failure due to target URL containing "error".'
        print(f"[{run_id}] Crawl failed for {target_url}")
    else:
        crawl_jobs[run_id]['status'] = 'complete'
        print(f"[{run_id}] Crawl complete for {target_url}")

# --- API Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Crawler Automation API!"}

@app.post("/crawl")
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to initiate a new web crawl.
    It accepts a JSON payload with 'target_url' and immediately returns a run_id.
    The actual crawling process runs in a background task.
    """
    target_url = request.target_url
    run_id = str(uuid.uuid4()) # Generate a unique ID for this crawl run

    # Initialize the job details in the in-memory dictionary
    crawl_jobs[run_id] = {
        'target_url': target_url,
        'status': 'pending', # Initial status
        'progress': 0,
        'results': [],
        'started_at': time.time(), # Record start time
        'error_message': None # Initialize error message
    }

    # Add the crawl simulation function to FastAPI's background tasks.
    # This allows the HTTP response to be sent instantly while the crawl runs.
    background_tasks.add_task(run_norconex_crawler_simulation, run_id, target_url)

    # Return a 202 Accepted response, indicating the request has been taken for processing.
    return JSONResponse(content={
        "message": "Crawl initiated successfully",
        "run_id": run_id,
        "status": "pending"
    }, status_code=202)

@app.get("/status/{run_id}")
async def get_crawl_status(run_id: str):
    """
    Endpoint to retrieve the current status of a specific crawl run.
    Returns status, progress, number of indexed pages, and any error messages.
    """
    job = crawl_jobs.get(run_id)

    # If the run_id is not found in our in-memory storage, return a 404 error.
    if not job:
        raise HTTPException(status_code=404, detail="Crawl run not found")

    # Return the current status details of the job
    return JSONResponse(content={
        "run_id": run_id,
        "target_url": job['target_url'],
        "status": job['status'],
        "progress": job['progress'],
        "started_at": job['started_at'],
        "num_pages_indexed": len(job['results']), # Count of pages currently indexed
        "error_message": job.get('error_message') # Get error message if exists
    })

@app.get("/results/{run_id}", response_model=list[PageRow])
async def get_crawl_results(run_id: str):
    """
    Endpoint to retrieve the simulated indexed pages (results) for a specific crawl run.
    Results are returned if the crawl is complete or still running with partial data.
    """
    job = crawl_jobs.get(run_id)

    # If the run_id is not found, return a 404 error.
    if not job:
        raise HTTPException(status_code=404, detail="Crawl run not found")

    # Return the results if the crawl is complete or still in progress (with partial results).
    # If it's pending or failed without results, return a 409 Conflict.
    if job['status'] in ['complete', 'running']:
        return job['results']
    else:
        raise HTTPException(status_code=409, detail="Crawl not yet complete or results not available")

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
        crawl4ai_sessions[run_id]["logs"].append(log_entry)

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

async def update_progress(run_id: str, pages_crawled: int, total_pages: int, crawl_speed: float = 0):
    """Update crawl progress and broadcast to WebSocket connections"""
    if run_id in crawl4ai_sessions:
        progress = crawl4ai_sessions[run_id]["progress"]
        progress["pages_crawled"] = pages_crawled
        progress["total_pages"] = total_pages
        progress["pages_remaining"] = max(0, total_pages - pages_crawled)
        progress["percentage"] = (pages_crawled / total_pages * 100) if total_pages > 0 else 0
        progress["crawl_speed"] = crawl_speed

        # Calculate estimated time remaining (in seconds)
        if crawl_speed > 0 and progress["pages_remaining"] > 0:
            progress["estimated_time_remaining"] = int((progress["pages_remaining"] / crawl_speed) * 60)
        else:
            progress["estimated_time_remaining"] = 0

        await broadcast_to_websockets(run_id, {
            "type": "progress",
            "progress": progress
        })

async def run_crawl4ai_agent_simulation(run_id: str, target_url: str):
    """
    Simulate the Crawl4AI agent process with realistic interaction
    """
    print(f"[Crawl4AI-{run_id}] Starting agent simulation for: {target_url}")

    try:
        # Initialize session
        await update_agent_status(run_id, "running")
        await add_agent_log(run_id, "🤖 Crawl4AI Agent initialized", "info")
        await asyncio.sleep(1)

        # Site reconnaissance
        await add_agent_log(run_id, "📋 Starting site reconnaissance...", "info")
        await asyncio.sleep(2)
        await add_agent_log(run_id, f"🔍 Analyzing {target_url}", "info")
        await asyncio.sleep(2)
        await add_agent_log(run_id, "✅ Site type detected: JavaScript-heavy banking site", "success")
        await asyncio.sleep(1)

        # Automatically proceed with full browser rendering
        await add_agent_log(run_id, "🚀 Starting full browser crawl...", "info")
        await asyncio.sleep(1)

        # Simulate crawling process with realistic progress
        pages = [
            "/ (Homepage)", "/business (Business)", "/personal (Personal)",
            "/loans (Loans)", "/cards (Credit Cards)", "/invest (Investments)",
            "/business/accounts (Business Accounts)", "/help (Help Center)",
            "/business/loans (Business Loans)", "/personal/accounts (Personal Accounts)",
            "/personal/home-loans (Home Loans)", "/business/business-banking (Business Banking)",
            "/about (About Us)", "/contact (Contact)", "/careers (Careers)",
            "/investor-relations (Investor Relations)", "/sustainability (Sustainability)",
            "/financial-wellbeing (Financial Wellbeing)", "/tools-calculators (Tools & Calculators)",
            "/security (Security)", "/support (Support Centre)"
        ]

        total_pages = len(pages)
        crawl_speed = 2.5  # pages per minute

        # Initialize progress
        await update_progress(run_id, 0, total_pages, crawl_speed)
        await add_agent_log(run_id, f"📊 Estimated {total_pages} pages to crawl at {crawl_speed} pages/min", "info")

        for i, page in enumerate(pages):
            await add_agent_log(run_id, f"📄 Crawling {page}", "info")

            # Update progress
            pages_crawled = i + 1
            await update_progress(run_id, pages_crawled, total_pages, crawl_speed)

            await asyncio.sleep(1.2)  # Realistic crawl timing

            if i == 3:  # Automatically include PDF documents
                await add_agent_log(run_id, "📄 Found PDF documents, including automatically", "info")
                await add_agent_log(run_id, "📄 Including PDF documents", "success")
                # Add extra pages for PDFs
                pages.extend([
                    "/documents/annual-report.pdf", "/documents/disclosure.pdf",
                    "/documents/terms-conditions.pdf", "/documents/privacy-policy.pdf"
                ])
                total_pages = len(pages)
                await update_progress(run_id, pages_crawled, total_pages, crawl_speed)

        # Complete the crawl
        await add_agent_log(run_id, "✅ Crawl completed successfully!", "success")
        await add_agent_log(run_id, f"📊 Quality Score: 92% (Excellent)", "success")
        await add_agent_log(run_id, f"📁 Output saved to: ./output/{target_url.replace('https://', '').replace('/', '_')}", "info")
        await update_agent_status(run_id, "completed")

    except Exception as e:
        await add_agent_log(run_id, f"❌ Error: {str(e)}", "error")
        await update_agent_status(run_id, "error")

@app.post("/crawl4ai/start")
async def start_crawl4ai(request: Crawl4AIRequest, background_tasks: BackgroundTasks):
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
        "progress": {
            "percentage": 0,
            "pages_crawled": 0,
            "pages_remaining": 0,
            "total_pages": 0,
            "estimated_time_remaining": 0,
            "crawl_speed": 0  # pages per minute
        }
    }

    # Initialize WebSocket connections list
    websocket_connections[run_id] = []

    # Start the agent simulation
    background_tasks.add_task(run_crawl4ai_agent_simulation, run_id, target_url)

    return JSONResponse(content={
        "run_id": run_id,
        "message": "Crawl4AI agent started",
        "status": "pending"
    }, status_code=202)

@app.get("/crawl4ai/status/{run_id}")
async def get_crawl4ai_status(run_id: str):
    """Get the current status of a Crawl4AI agent session"""
    if run_id not in crawl4ai_sessions:
        raise HTTPException(status_code=404, detail="Crawl4AI session not found")

    session = crawl4ai_sessions[run_id]
    return JSONResponse(content={
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

