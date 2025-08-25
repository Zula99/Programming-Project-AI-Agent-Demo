from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

#-----AI imports-----
from pydantic import BaseModel
from agents.config_agent import generate_norconex_V3_config
from services.indexer import index_crawl_results_to_opensearch


import uuid # For generating unique IDs
import time # For simulating time-based operations
import threading # For running the simulation in a separate thread
import subprocess # For running external commands
import os # For environment variables
import tempfile # For temporary files

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

# --- Helper Function: Runs the Norconex Crawler via Maven ---
def run_norconex_crawler_maven(run_id: str, target_url: str):
    """
    This function runs the actual Norconex crawler via the Maven-based runner.
    It generates a configuration file, executes the crawler, and monitors progress.
    """
    print(f"[{run_id}] Starting crawl for: {target_url}")
    
    # Update job status to 'running' and reset progress
    crawl_jobs[run_id]['status'] = 'running'
    crawl_jobs[run_id]['progress'] = 0

    try:
        # Generate Norconex XML configuration
        print(f"[{run_id}] Generating Norconex configuration...")
        xml_config = generate_norconex_V3_config(
            url=target_url,
            max_depth=3,
            max_documents=500,
            index_name="demo_factory",
            keep_downloads=True
        )
        
        # Write config to temporary file
        config_dir = "/opt/norconex/configs"
        if not os.path.exists(config_dir):
            config_dir = "./norconex_configs"  # Fallback for development
            os.makedirs(config_dir, exist_ok=True)
            
        config_file = os.path.join(config_dir, f"crawler-{run_id}.xml")
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(xml_config)
        print(f"[{run_id}] Configuration saved to: {config_file}")
        
        # Determine how to run the crawler based on environment
        norconex_mode = os.environ.get('NORCONEX_MODE', 'maven')
        
        if norconex_mode == 'maven':
            # Make HTTP request to norconex-maven container to trigger crawl
            import requests
            try:
                # Send config file path to norconex-maven service via HTTP
                norconex_response = requests.post(
                    "http://norconex-maven:8080/crawl",
                    json={"config_path": f"/opt/norconex/configs/crawler-{run_id}.xml"},
                    timeout=300  # 5 minute timeout
                )
                
                if norconex_response.status_code == 200:
                    crawl_jobs[run_id]['status'] = 'complete'
                    crawl_jobs[run_id]['progress'] = 100
                    print(f"[{run_id}] Crawl completed successfully via HTTP API")
                else:
                    raise Exception(f"HTTP API error: {norconex_response.status_code} - {norconex_response.text}")
                    
            except Exception as e:
                # Fallback: Use file-based trigger
                print(f"[{run_id}] HTTP API failed, trying file-based approach: {e}")
                
                # Create a trigger file that the norconex container can monitor
                trigger_file = f"/opt/norconex/configs/trigger-{run_id}.json"
                trigger_data = {
                    "run_id": run_id,
                    "config_path": f"/opt/norconex/configs/crawler-{run_id}.xml",
                    "target_url": target_url
                }
                
                with open(trigger_file, 'w') as f:
                    import json
                    json.dump(trigger_data, f)
                
                print(f"[{run_id}] Created trigger file: {trigger_file}")
                
                # Wait for completion (simplified - check for completion file)
                import time
                max_wait_time = 300  # 5 minutes
                wait_interval = 5  # 5 seconds
                total_waited = 0
                
                completion_file = f"/opt/norconex/configs/completed-{run_id}.json"
                
                while total_waited < max_wait_time:
                    if os.path.exists(completion_file):
                        print(f"[{run_id}] Found completion file")
                        break
                    time.sleep(wait_interval)
                    total_waited += wait_interval
                    crawl_jobs[run_id]['progress'] = min(90, 10 + (total_waited * 80 // max_wait_time))
                
                if os.path.exists(completion_file):
                    crawl_jobs[run_id]['status'] = 'complete'
                    crawl_jobs[run_id]['progress'] = 100
                    print(f"[{run_id}] Crawl completed successfully via file trigger")
                else:
                    raise Exception("Crawl timed out - no completion file found")
                    
            # Skip the subprocess execution since we handled it above
            return
        else:
            # Fallback to direct Java execution for development
            cmd = [
                "java", "-jar", "./norconex-runner/runner/target/runner-1.0.0-SNAPSHOT.jar",
                config_file
            ]
        
        print(f"[{run_id}] Executing command: {' '.join(cmd)}")
        
        # Update progress to indicate crawler has started
        crawl_jobs[run_id]['progress'] = 10
        
        # Execute the crawler
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor the process and update progress
        stdout_lines = []
        stderr_lines = []
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                stdout_lines.append(output.strip())
                print(f"[{run_id}] {output.strip()}")
                
                # Update progress based on log output (simple heuristic)
                if len(stdout_lines) > 0:
                    # Gradually increase progress as we get more log lines
                    base_progress = min(90, 10 + (len(stdout_lines) * 2))
                    crawl_jobs[run_id]['progress'] = base_progress
        
        # Get any remaining output
        stdout, stderr = process.communicate()
        if stdout:
            stdout_lines.extend(stdout.strip().split('\n') if stdout.strip() else [])
        if stderr:
            stderr_lines.extend(stderr.strip().split('\n') if stderr.strip() else [])
        
        # Check return code
        return_code = process.returncode
        
        if return_code == 0:
            crawl_jobs[run_id]['status'] = 'complete'
            crawl_jobs[run_id]['progress'] = 100
            print(f"[{run_id}] Crawl completed successfully")
            
            # Automatically index the crawl results to OpenSearch
            try:
                print(f"[{run_id}] Starting automatic indexing to OpenSearch...")
                indexing_result = index_crawl_results_to_opensearch(run_id)
                
                crawl_jobs[run_id]['indexing_result'] = indexing_result
                crawl_jobs[run_id]['num_pages_indexed'] = indexing_result.get('indexed', 0)
                
                print(f"[{run_id}] Indexing completed: {indexing_result.get('indexed', 0)} documents indexed")
                
                # Create results based on indexing
                crawl_jobs[run_id]['results'] = [
                    {"id": str(i), "path": f"/page{i}", "title": f"Indexed Page {i}", "type": "html", "size": 15000 + (i * 1000)}
                    for i in range(1, indexing_result.get('indexed', 0) + 1)
                ]
                
            except Exception as e:
                print(f"[{run_id}] Warning: Automatic indexing failed: {e}")
                # Still mark crawl as complete, but note the indexing failure
                crawl_jobs[run_id]['indexing_error'] = str(e)
                crawl_jobs[run_id]['results'] = [
                    {"id": "1", "path": "/", "title": "Home Page", "type": "html", "size": 18322},
                    {"id": "2", "path": "/about", "title": "About Us", "type": "html", "size": 25101},
                ]
        else:
            crawl_jobs[run_id]['status'] = 'failed'
            crawl_jobs[run_id]['error_message'] = f"Crawler failed with return code {return_code}"
            if stderr_lines:
                crawl_jobs[run_id]['error_message'] += f": {'; '.join(stderr_lines[-3:])}"
            print(f"[{run_id}] Crawl failed with return code {return_code}")
            
    except Exception as e:
        crawl_jobs[run_id]['status'] = 'failed'
        crawl_jobs[run_id]['error_message'] = str(e)
        print(f"[{run_id}] Crawl failed with exception: {e}")
        
    finally:
        # Clean up config file
        if 'config_file' in locals() and os.path.exists(config_file):
            try:
                os.remove(config_file)
                print(f"[{run_id}] Cleaned up config file: {config_file}")
            except:
                pass

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

    # Add the crawl function to FastAPI's background tasks.
    # This allows the HTTP response to be sent instantly while the crawl runs.
    background_tasks.add_task(run_norconex_crawler_maven, run_id, target_url)

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
    

class GenConfigRequest(BaseModel):
    url: str
    max_depth: int = 3
    max_documents: int = 500
    index_name: str = "demo_factory"
    keep_downloads: bool = True

@app.post("/config/generate")
async def config_generate(req: GenConfigRequest):
    """
    Generates a Norconex v3 XML config using a LangChain agent (OpenAI backend).
    """
    xml = generate_norconex_V3_config(
        url=req.url,
        max_depth=req.max_depth,
        max_documents=req.max_documents,
        index_name=req.index_name,
        keep_downloads=req.keep_downloads,
    )
    return {"xml": xml, "provider": "openai-langchain"}

