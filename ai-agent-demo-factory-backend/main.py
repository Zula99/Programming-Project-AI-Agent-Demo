from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid # For generating unique IDs
import time # For simulating time-based operations
import threading # For running the simulation in a separate thread
import httpx # For auto-proxy integration

# Initialize FastAPI app
app = FastAPI()

# Configure CORS 
# Adjust the 'origins' list to include the actual URL(s) where your frontend is hosted.
origins = [
    "http://localhost",
    "http://localhost:3000", 
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

