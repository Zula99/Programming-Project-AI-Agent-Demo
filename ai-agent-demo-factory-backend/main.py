from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

#-----Core imports-----
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

def create_config_from_nab_template(url: str, max_depth: int = 3, max_documents: int = 500, 
                                  index_name: str = "demo_factory") -> str:
    """
    Create a Norconex config using the NAB template as a base.
    """
    
    # Copy working-example.xml and modify it to ONLY crawl the target URL
    try:
        with open("/opt/norconex/configs/working-example.xml", 'r') as f:
            config = f.read()
        
        # Replace the URL and index name
        config = config.replace('<url>https://example.com/</url>', f'<url>{url}</url>')
        config = config.replace('indexName>demo_factory</indexName>', f'indexName>{index_name}</indexName>')
        
        # Fix the domain restrictions to ONLY allow the target URL's domain
        import re
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        target_domain = parsed_url.netloc
        
        # Create unique collector and crawler IDs based on domain
        domain_safe = target_domain.replace('.', '-').replace('www-', '')
        collector_id = f"collector-{domain_safe}"
        crawler_id = f"crawler-{domain_safe}"
        
        # Replace collector and crawler IDs for domain-specific datastores
        config = config.replace('id="nab-banking-collector"', f'id="{collector_id}"')
        config = config.replace('id="nab-banking-crawler"', f'id="{crawler_id}"')
        
        # Set reasonable but limited crawl parameters for testing
        config = config.replace('<maxDocuments>5000</maxDocuments>', '<maxDocuments>50</maxDocuments>')
        config = config.replace('<maxDepth>8</maxDepth>', '<maxDepth>2</maxDepth>')
        
        # Ensure stayOnDomain is true and add domain restriction
        config = config.replace('stayOnDomain="true"', 'stayOnDomain="true"')
        
        # Add a reference filter to ONLY allow the target domain
        reference_filter = f'''
    <!-- Reference filters - ONLY allow target domain -->
    <referenceFilters>
        <filter class="com.norconex.collector.core.filter.impl.ReferenceFilter" onMatch="include">
            <valueMatcher method="regex">^https?://([a-z0-9-]+\.)*{re.escape(target_domain.replace('www.', ''))}(/.*)?$</valueMatcher>
        </filter>
        <filter class="com.norconex.collector.core.filter.impl.ExtensionReferenceFilter" onMatch="exclude">
            css,js,png,jpg,jpeg,gif,ico,zip,exe,svg,webp,mp4,mp3,woff,woff2
        </filter>
    </referenceFilters>'''
        
        # Replace the existing referenceFilters section
        config = re.sub(
            r'<referenceFilters>.*?</referenceFilters>',
            reference_filter,
            config,
            flags=re.DOTALL
        )
        
        return config
        
    except Exception as e:
        print(f"Error reading working-example template: {e}")
        return f'<!-- Error: {e} -->'
    
    return config

# Pydantic model for validating the request body when starting a crawl.
# FastAPI uses this to automatically validate incoming JSON data.
class CrawlRequest(BaseModel):
    target_url: str

# Pydantic model for search requests
class SearchRequest(BaseModel):
    query: str
    size: int = 50

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
        # Use the NAB config as template and modify for the target URL
        print(f"[{run_id}] Using NAB config template...")
        xml_config = create_config_from_nab_template(
            url=target_url,
            max_depth=3,
            max_documents=500,
            index_name="demo_factory"
        )
        
        # Write config to temporary file
        config_dir = "/opt/norconex/configs"
        if not os.path.exists(config_dir):
            config_dir = "./norconex-runner/configs"  # Fallback for development
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
                max_wait_time = 900  # 15 minutes
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
                    
                    # Documents are committed directly to OpenSearch by ElasticsearchCommitter
                    print(f"[{run_id}] Documents committed directly to OpenSearch via ElasticsearchCommitter")
                    crawl_jobs[run_id]['indexing_result'] = {"indexed": "direct", "note": "ElasticsearchCommitter handles indexing"}
                    crawl_jobs[run_id]['num_pages_indexed'] = "direct"
                        
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
            
            # Documents committed directly to OpenSearch by ElasticsearchCommitter
            print(f"[{run_id}] Documents committed directly to OpenSearch via ElasticsearchCommitter")
            crawl_jobs[run_id]['indexing_result'] = {"indexed": "direct", "note": "ElasticsearchCommitter handles indexing"}
            crawl_jobs[run_id]['num_pages_indexed'] = "direct"
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
        # Leave config file for Norconex to use
        print(f"[{run_id}] Keeping config file for Norconex: {config_file if 'config_file' in locals() else 'N/A'}")

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

@app.post("/search")
async def search_documents(request: SearchRequest):
    """
    Search documents in OpenSearch index.
    """
    try:
        # OpenSearch query
        search_body = {
            "size": request.size,
            "query": {
                "multi_match": {
                    "query": request.query,
                    "fields": ["title^2", "content", "url"],
                    "type": "best_fields"
                }
            },
            "highlight": {
                "fields": {
                    "title": {},
                    "content": {"fragment_size": 150, "number_of_fragments": 2}
                }
            }
        }
        
        # Make request to OpenSearch
        response = requests.post(
            "http://opensearch:9200/demo_factory/_search",
            json=search_body,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"OpenSearch error: {response.text}")
            
        search_results = response.json()
        
        # Format results for frontend
        documents = []
        for hit in search_results["hits"]["hits"]:
            source = hit["_source"]
            highlight = hit.get("highlight", {})
            
            documents.append({
                "id": hit["_id"],
                "url": source.get("url", ""),
                "title": source.get("title", [""])[0] if isinstance(source.get("title"), list) else source.get("title", ""),
                "content": source.get("content", ""),
                "score": hit["_score"],
                "highlight": {
                    "title": highlight.get("title", []),
                    "content": highlight.get("content", [])
                }
            })
        
        return {
            "total": search_results["hits"]["total"]["value"],
            "documents": documents,
            "query": request.query
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to OpenSearch: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


