from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import sys
import os

#-----Core imports-----
from services.log_indexer import index_crawl_logs_to_opensearch, search_crawl_logs
from services.cms_detector import CMSDetector
from services.schema_processor import Search365SchemaProcessor

# Import WebSocket log handler
from norconex_websocket_log_handler import websocket_connections, setup_websocket_logging, log_buffer


import uuid # For generating unique IDs
import time # For time tracking and delays
import threading # Unused - can be removed
import subprocess # For running external commands (development mode)
import tempfile # Unused - can be removed
import re # For regex parsing in config generation and log parsing
import json # For JSON parsing in WebSocket messages
import asyncio # For async operations
import logging # For structured logging to WebSocket

# Create logger for backend operations
logger = logging.getLogger(__name__)

def extract_crawl_statistics(run_id: str) -> dict:
    """
    Extract crawl-specific statistics from Norconex logs for the specific run_id.
    Returns individual crawl stats, not the entire index stats.
    """
    stats = {}
    try:
        # Read the trigger log to find the execution summary for this specific run
        log_file = "/opt/norconex/logs/trigger.log"
        if not os.path.exists(log_file):
            print(f"[{run_id}] No trigger log found")
            return stats
        
        with open(log_file, 'r') as f:
            content = f.read()
        
        # Find the section that mentions this specific run_id completion
        run_pattern = rf'Crawl (?:completed successfully|failed) for {re.escape(run_id)}'
        run_match = re.search(run_pattern, content)
        
        if not run_match:
            print(f"[{run_id}] Could not find run completion marker in logs")
            return stats
        
        # Work backwards from the completion marker to find the execution summary
        content_before = content[:run_match.start()]
        
        # Look for the most recent execution summary before this completion  
        # Updated pattern to match the actual log format
        summary_pattern = r'Execution Summary:\s*\nTotal processed:\s*(\d+)\s*\nSince.*?\n\s*Crawl duration:\s*([^\n]+)\n\s*Avg\. throughput:\s*([^\n]+)\n\s*Event counts:\s*\n((?:\s*[A-Z_]+:\s*\d+\s*\n)*)'
        
        matches = list(re.finditer(summary_pattern, content_before, re.MULTILINE | re.DOTALL))
        if not matches:
            print(f"[{run_id}] No execution summary found in logs")
            return stats
        
        # Use the most recent execution summary (should be for this run)
        latest_match = matches[-1]
        total_processed = int(latest_match.group(1))
        duration_str = latest_match.group(2).strip()
        throughput_str = latest_match.group(3).strip()
        events_section = latest_match.group(4)
        
        # Basic stats
        stats['total_pages_crawled'] = total_processed
        
        # Parse event counts from the events section
        event_patterns = {
            'pages_indexed': r'DOCUMENT_COMMITTED_UPSERT:\s*(\d+)',
            'pages_fetched': r'DOCUMENT_FETCHED:\s*(\d+)', 
            'pages_processed': r'DOCUMENT_PROCESSED:\s*(\d+)',
            'pages_queued': r'DOCUMENT_QUEUED:\s*(\d+)',
            'urls_extracted': r'URLS_EXTRACTED:\s*(\d+)',
            'pages_rejected': r'REJECTED_FILTER:\s*(\d+)',
        }
        
        for stat_name, pattern in event_patterns.items():
            match = re.search(pattern, events_section)
            if match:
                stats[stat_name] = int(match.group(1))
        
        # Parse throughput 
        throughput_match = re.search(r'([0-9.]+)\s+processed/seconds', throughput_str)
        if throughput_match:
            stats['avg_throughput'] = float(throughput_match.group(1))
        
        # Parse duration
        if 'minute' in duration_str and 'second' in duration_str:
            duration_match = re.search(r'(\d+)\s+minutes?\s+and\s+(\d+)\s+seconds?', duration_str)
            if duration_match:
                minutes = int(duration_match.group(1))
                seconds = int(duration_match.group(2))
                stats['norconex_duration_seconds'] = minutes * 60 + seconds
        elif 'second' in duration_str:
            duration_match = re.search(r'(\d+)\s+seconds?', duration_str)
            if duration_match:
                stats['norconex_duration_seconds'] = int(duration_match.group(1))
        
        print(f"[{run_id}] Extracted crawl stats: {stats}")
        
    except Exception as e:
        print(f"[{run_id}] Failed to extract crawl statistics: {e}")
        import traceback
        print(f"[{run_id}] Traceback: {traceback.format_exc()}")
    
    return stats

# Initialize FastAPI app
app = FastAPI()

# Setup WebSocket logging
setup_websocket_logging()

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


# Dictionary stores crawl statuses and results in memory (not persistent across restarts)
crawl_jobs = {}

# Dictionary to track running processes for stop functionality
running_processes = {}

def create_config_from_nab_template(url: str, max_depth: int = 3, max_documents: int = 500,
                                  index_name: str = "demo_factory", template: Optional["TemplateConfig"] = None, run_id: str = None) -> str:
    """
    Create a Norconex config using base-crawl-template as the base.
    Always uses demo_factory_raw index for raw data extraction.
    If template is provided, use template parameters; otherwise use defaults.
    """

    # Always use base-crawl-template for maximum data extraction
    template_file = "base-crawl-template.xml"

    # Use template parameters if provided, otherwise use function defaults
    if template:
        max_depth = template.maxDepth
        max_documents = template.maxDocuments
        num_threads = template.numThreads
        delay_ms = template.delay
        stay_on_domain = template.stayOnDomain
        include_subdomains = template.includeSubdomains
        file_exclusions = template.fileExclusions
        url_patterns = template.urlPatterns
        print(f"Using base-crawl-template with '{template.name}' ({template.platform}) parameters: depth={max_depth}, docs={max_documents}, threads={num_threads}")
    else:
        # Default values for base-crawl-template
        num_threads = 4
        delay_ms = 2000
        stay_on_domain = True
        include_subdomains = False
        file_exclusions = []
        url_patterns = []
        print(f"Using base-crawl-template with default parameters: depth={max_depth}, docs={max_documents}")

    try:
        template_path = f"/opt/norconex/configs/{template_file}"

        # Fallback for development environment
        if not os.path.exists(template_path):
            template_path = f"./norconex-runner/configs/{template_file}"
        
        with open(template_path, 'r') as f:
            config = f.read()
        
        # Parse URL first to get domain info
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        target_domain = parsed_url.netloc

        # Replace the URL - handle multiple possible template URLs
        config = config.replace('<url>https://example.com/</url>', f'<url>{url}</url>')
        config = config.replace('<url>https://example.com</url>', f'<url>{url}</url>')

        # Always use demo_factory_raw for base-crawl template (raw data extraction)
        config = config.replace('<indexName>demo_factory</indexName>', '<indexName>demo_factory_raw</indexName>')

        # Inject run_id for tracking if provided
        if run_id:
            config = config.replace('<constant name="run_id">PLACEHOLDER_RUN_ID</constant>',
                                  f'<constant name="run_id">{run_id}</constant>')

        # Also replace domain in regex patterns (handle both escaped and unescaped)
        escaped_domain = target_domain.replace('.', '\\.')
        config = config.replace('example\\.com', escaped_domain)
        config = config.replace('example.com', target_domain)
        
        # Create unique collector and crawler IDs based on domain
        domain_safe = target_domain.replace('.', '-').replace('www-', '')
        collector_id = f"base-crawl-collector-{domain_safe}"
        crawler_id = f"base-crawl-extractor-{domain_safe}"

        # Replace collector and crawler IDs for base-crawl template
        config = config.replace('id="base-crawl-collector"', f'id="{collector_id}"')
        config = config.replace('id="base-crawl-extractor"', f'id="{crawler_id}"')
        
        # Set crawl parameters for base-crawl-template
        config = config.replace('<maxDocuments>500</maxDocuments>', f'<maxDocuments>{max_documents}</maxDocuments>')
        config = config.replace('<maxDepth>3</maxDepth>', f'<maxDepth>{max_depth}</maxDepth>')
        config = config.replace('<numThreads>4</numThreads>', f'<numThreads>{num_threads}</numThreads>')

        # Set delay - base-crawl uses "2 seconds" format
        config = config.replace('default="2 seconds"', f'default="{delay_ms} milliseconds"')
        
        # Set domain restrictions (use template values if available)
        if template:
            stay_domain_str = "true" if stay_on_domain else "false"
            include_sub_str = "true" if include_subdomains else "false"
            config = config.replace('stayOnDomain="true"', f'stayOnDomain="{stay_domain_str}"')
            config = config.replace('includeSubdomains="false"', f'includeSubdomains="{include_sub_str}"')
        else:
            # Default behavior
            config = config.replace('stayOnDomain="true"', 'stayOnDomain="true"')
        
        # Add a reference filter to ONLY allow the target domain
        # Build file exclusions list
        if template and template.fileExclusions:
            # Use template-specific exclusions plus default media files
            exclusions = ','.join(template.fileExclusions + ['css', 'js', 'png', 'jpg', 'jpeg', 'gif', 'ico', 'zip', 'exe', 'svg', 'webp', 'mp4', 'mp3', 'woff', 'woff2'])
        else:
            # Default exclusions
            exclusions = 'css,js,png,jpg,jpeg,gif,ico,zip,exe,svg,webp,mp4,mp3,woff,woff2'
        
        reference_filter = f'''
    <!-- Reference filters - ONLY allow target domain -->
    <referenceFilters>
        <filter class="com.norconex.collector.core.filter.impl.ReferenceFilter" onMatch="include">
            <valueMatcher method="regex">^https?://([a-z0-9-]+\\.)*{re.escape(target_domain.replace('www.', ''))}(/.*)?$</valueMatcher>
        </filter>
        <filter class="com.norconex.collector.core.filter.impl.ExtensionReferenceFilter" onMatch="exclude">
            {exclusions}
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
        print(f"Error reading base-crawl-template: {e}")
        # Fallback to a basic config if template is not found
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- Fallback config - Error: {e} -->
<httpcollector id="fallback-collector">
    <workDir>/opt/norconex/data/workdir</workDir>
    <crawlers>
        <crawler id="fallback-crawler">
            <startURLs stayOnDomain="true">
                <url>{url}</url>
            </startURLs>
            <maxDocuments>{max_documents}</maxDocuments>
            <maxDepth>{max_depth}</maxDepth>
            <committers>
                <committer class="com.norconex.committer.elasticsearch.ElasticsearchCommitter">
                    <nodes>http://opensearch:9200</nodes>
                    <indexName>{index_name}</indexName>
                </committer>
            </committers>
        </crawler>
    </crawlers>
</httpcollector>'''

# FastAPI uses this to automatically validate incoming JSON data.
class CrawlRequest(BaseModel):
    target_url: str
    template: Optional["TemplateConfig"] = None  # CMS template config from frontend

# Pydantic model for search requests
class SearchRequest(BaseModel):
    query: str
    size: int = 50

# Template configuration model
class TemplateConfig(BaseModel):
    id: str
    name: str
    platform: str
    maxDepth: int
    maxDocuments: int
    numThreads: int
    delay: int
    stayOnDomain: bool
    includeSubdomains: bool
    fileExclusions: list[str]
    urlPatterns: list[str]

# Pydantic model for crawl log search requests
class CrawlLogSearchRequest(BaseModel):
    run_id: Optional[str] = None
    log_level: Optional[str] = None
    log_type: Optional[str] = None  # "trigger", "runner", "execution_summary"
    size: int = 100

# Pydantic model for CMS detection requests
class CMSDetectionRequest(BaseModel):
    url: str
    timeout: Optional[int] = 10

# Pydantic model for the structure of a single page result.
# Used for documenting and validating the 'results' array.
class PageRow(BaseModel):
    id: str
    path: str
    title: str
    type: str # e.g., "html", "pdf", "doc"
    size: int # size in bytes

# --- Helper Function: Runs the Norconex Crawler via Maven ---
async def tail_norconex_logs(run_id: str):
    """Tail Norconex logs and broadcast to WebSocket clients"""
    log_file = "/opt/norconex/logs/trigger.log"

    # Get the target URL for this crawl to filter logs
    target_url = crawl_jobs[run_id].get('target_url', '')
    # Extract domain from URL for filtering
    try:
        from urllib.parse import urlparse
        domain = urlparse(target_url).netloc.replace('www.', '')
    except:
        domain = target_url

    logger.info(f"[{run_id}] Starting Norconex log tail for domain: {domain}")

    try:
        # Start from the end of the file
        with open(log_file, 'r') as f:
            # Move to end
            f.seek(0, 2)

            while run_id in crawl_jobs and crawl_jobs[run_id]['status'] == 'running':
                line = f.readline()
                if line:
                    # Parse Norconex log line and broadcast
                    # Filter by run_id OR domain in URL
                    if run_id in line or domain in line:
                        # Extract timestamp and message
                        parts = line.strip().split(maxsplit=3)
                        if len(parts) >= 4:
                            timestamp = parts[0]
                            level = parts[2]
                            message = parts[3] if len(parts) > 3 else line.strip()

                            log_entry = {
                                "timestamp": timestamp,
                                "level": level,
                                "source": "norconex",
                                "message": message
                            }

                            # Broadcast to WebSocket
                            if run_id in websocket_connections:
                                for ws in websocket_connections[run_id]:
                                    try:
                                        await ws.send_text(json.dumps({
                                            "type": "backend_log",
                                            "log": log_entry
                                        }))
                                    except:
                                        pass
                else:
                    await asyncio.sleep(0.1)  # Wait for new lines
    except Exception as e:
        logger.error(f"[{run_id}] Error tailing Norconex logs: {e}")

async def run_norconex_crawler_maven(run_id: str, target_url: str, template: Optional["TemplateConfig"] = None):
    """
    This function runs the actual Norconex crawler via the Maven-based runner.
    It generates a configuration file, executes the crawler, and monitors progress.
    """
    logger.info(f"[{run_id}] Starting crawl for: {target_url}")

    # Update job status to 'running' and reset progress
    crawl_jobs[run_id]['status'] = 'running'
    crawl_jobs[run_id]['progress'] = 0

    # Initialize process tracking
    running_processes[run_id] = None

    # Start tailing Norconex logs in background
    asyncio.create_task(tail_norconex_logs(run_id))

    try:
        # Generate Norconex config from base-crawl-template with optional CMS parameters
        if template:
            logger.info(f"[{run_id}] Using template '{template.name}' ({template.platform})...")
        else:
            logger.info(f"[{run_id}] Using base-crawl-template with defaults...")

        xml_config = create_config_from_nab_template(
            url=target_url,
            max_depth=3,
            max_documents=500,
            index_name="demo_factory",
            template=template,
            run_id=run_id
        )
        
        # Write config file for this crawl run
        config_dir = "/opt/norconex/configs"
        if not os.path.exists(config_dir):
            config_dir = "./norconex-runner/configs"  # Fallback for development
            os.makedirs(config_dir, exist_ok=True)
            
        config_file = os.path.join(config_dir, f"crawler-{run_id}.xml")
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(xml_config)
        logger.info(f"[{run_id}] Configuration saved to: {config_file}")
        
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
                    crawl_jobs[run_id]['completed_at'] = time.time()

                    # Calculate final stats
                    duration = crawl_jobs[run_id]['completed_at'] - crawl_jobs[run_id]['started_at']
                    crawl_jobs[run_id]['stats']['crawl_duration_seconds'] = round(duration, 2)
                    
                    # Extract real crawl statistics from logs
                    crawl_jobs[run_id]['stats'].update(extract_crawl_statistics(run_id))
                    
                    # Index crawl logs to OpenSearch
                    try:
                        log_indexing_result = index_crawl_logs_to_opensearch(run_id)
                        crawl_jobs[run_id]['log_indexing_result'] = log_indexing_result
                        print(f"[{run_id}] Crawl logs indexed: {log_indexing_result}")
                    except Exception as e:
                        print(f"[{run_id}] Failed to index crawl logs: {e}")

                    # Automatically process raw data to Search365 schema
                    try:
                        print(f"[{run_id}] Starting automatic schema processing...")
                        processor = Search365SchemaProcessor()
                        processing_result = processor.process_crawl_to_main_index(run_id)
                        crawl_jobs[run_id]['processing_result'] = processing_result
                        crawl_jobs[run_id]['processing_completed'] = True
                        print(f"[{run_id}] Schema processing completed: {processing_result['processed_documents']} documents processed")
                    except Exception as e:
                        print(f"[{run_id}] Failed to process schema: {e}")
                        crawl_jobs[run_id]['processing_error'] = str(e)

                    print(f"[{run_id}] Crawl completed successfully via HTTP API")
                else:
                    raise Exception(f"HTTP API error: {norconex_response.status_code} - {norconex_response.text}")
                    
            except Exception as e:
                # Fallback: Use file-based trigger
                logger.warning(f"[{run_id}] HTTP API failed, trying file-based approach: {e}")
                
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
                
                logger.info(f"[{run_id}] Created trigger file: {trigger_file}")
                
                # Wait for completion (simplified - check for completion file)
                import time
                max_wait_time = 900  # 15 minutes
                wait_interval = 5  # 5 seconds
                total_waited = 0
                
                completion_file = f"/opt/norconex/configs/completed-{run_id}.json"
                
                while total_waited < max_wait_time:
                    if os.path.exists(completion_file):
                        logger.info(f"[{run_id}] Found completion file")
                        break
                    await asyncio.sleep(wait_interval)
                    total_waited += wait_interval
                    crawl_jobs[run_id]['progress'] = min(90, 10 + (total_waited * 80 // max_wait_time))
                
                if os.path.exists(completion_file):
                    crawl_jobs[run_id]['status'] = 'complete'
                    crawl_jobs[run_id]['progress'] = 100
                    crawl_jobs[run_id]['completed_at'] = time.time()
                    
                    # Calculate final stats
                    duration = crawl_jobs[run_id]['completed_at'] - crawl_jobs[run_id]['started_at']
                    crawl_jobs[run_id]['stats']['crawl_duration_seconds'] = round(duration, 2)
                    
                    # Extract real crawl statistics from logs
                    crawl_jobs[run_id]['stats'].update(extract_crawl_statistics(run_id))
                    
                    # Index crawl logs to OpenSearch
                    try:
                        log_indexing_result = index_crawl_logs_to_opensearch(run_id)
                        crawl_jobs[run_id]['log_indexing_result'] = log_indexing_result
                        print(f"[{run_id}] Crawl logs indexed: {log_indexing_result}")
                    except Exception as e:
                        print(f"[{run_id}] Failed to index crawl logs: {e}")

                    # Automatically process raw data to Search365 schema
                    try:
                        print(f"[{run_id}] Starting automatic schema processing...")
                        processor = Search365SchemaProcessor()
                        processing_result = processor.process_crawl_to_main_index(run_id)
                        crawl_jobs[run_id]['processing_result'] = processing_result
                        crawl_jobs[run_id]['processing_completed'] = True
                        print(f"[{run_id}] Schema processing completed: {processing_result['processed_documents']} documents processed")
                    except Exception as e:
                        print(f"[{run_id}] Failed to process schema: {e}")
                        crawl_jobs[run_id]['processing_error'] = str(e)

                    logger.info(f"[{run_id}] Crawl completed successfully via file trigger")

                    # Raw data was committed to demo_factory_raw by ElasticsearchCommitter
                    # Enriched data is now in demo_factory via schema_processor
                    print(f"[{run_id}] Raw data in demo_factory_raw, enriched data in demo_factory")
                    crawl_jobs[run_id]['indexing_result'] = {"indexed": "direct", "note": "ElasticsearchCommitter handles indexing"}
                    crawl_jobs[run_id]['num_pages_indexed'] = "direct"
                        
                else:
                    # Check for failure file
                    failure_file = f"/opt/norconex/configs/failed-{run_id}.json"
                    if os.path.exists(failure_file):
                        crawl_jobs[run_id]['status'] = 'failed'
                        crawl_jobs[run_id]['completed_at'] = time.time()
                        
                        # Calculate duration even for failed runs
                        duration = crawl_jobs[run_id]['completed_at'] - crawl_jobs[run_id]['started_at']
                        crawl_jobs[run_id]['stats']['crawl_duration_seconds'] = round(duration, 2)
                        
                        # Extract partial crawl statistics from logs
                        crawl_jobs[run_id]['stats'].update(extract_crawl_statistics(run_id))
                        
                        # Read failure details
                        try:
                            with open(failure_file, 'r') as f:
                                import json
                                failure_data = json.load(f)
                                crawl_jobs[run_id]['error_message'] = failure_data.get('error', 'Unknown error')
                                crawl_jobs[run_id]['failure_details'] = failure_data
                        except Exception as e:
                            crawl_jobs[run_id]['error_message'] = f"Crawl failed but could not read failure details: {e}"
                        
                        logger.warning(f"[{run_id}] Crawl failed - partial data may be available")
                    else:
                        raise Exception("Crawl timed out - no completion or failure file found")
                    
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
        
        # Store process reference for stop functionality
        running_processes[run_id] = process
        
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
            crawl_jobs[run_id]['completed_at'] = time.time()

            # Calculate final stats
            duration = crawl_jobs[run_id]['completed_at'] - crawl_jobs[run_id]['started_at']
            crawl_jobs[run_id]['stats']['crawl_duration_seconds'] = round(duration, 2)

            # Extract real crawl statistics from logs
            crawl_jobs[run_id]['stats'].update(extract_crawl_statistics(run_id))

            # Automatically process raw data to Search365 schema
            try:
                print(f"[{run_id}] Starting automatic schema processing...")
                processor = Search365SchemaProcessor()
                processing_result = processor.process_crawl_to_main_index(run_id)
                crawl_jobs[run_id]['processing_result'] = processing_result
                crawl_jobs[run_id]['processing_completed'] = True
                print(f"[{run_id}] Schema processing completed: {processing_result['processed_documents']} documents processed")
            except Exception as e:
                print(f"[{run_id}] Failed to process schema: {e}")
                crawl_jobs[run_id]['processing_error'] = str(e)

            logger.info(f"[{run_id}] Crawl completed successfully")

            # Raw data was committed to demo_factory_raw by ElasticsearchCommitter
            # Enriched data is now in demo_factory via schema_processor
            print(f"[{run_id}] Raw data in demo_factory_raw, enriched data in demo_factory")
            crawl_jobs[run_id]['indexing_result'] = {"indexed": "direct", "note": "ElasticsearchCommitter handles indexing"}
            crawl_jobs[run_id]['num_pages_indexed'] = "direct"
        else:
            crawl_jobs[run_id]['status'] = 'failed'
            crawl_jobs[run_id]['error_message'] = f"Crawler failed with return code {return_code}"
            if stderr_lines:
                crawl_jobs[run_id]['error_message'] += f": {'; '.join(stderr_lines[-3:])}"
            logger.error(f"[{run_id}] Crawl failed with return code {return_code}")
            
    except Exception as e:
        crawl_jobs[run_id]['status'] = 'failed'
        crawl_jobs[run_id]['error_message'] = str(e)
        logger.error(f"[{run_id}] Crawl failed with exception: {e}")

    finally:
        # Clean up process tracking
        if run_id in running_processes:
            del running_processes[run_id]
        
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
    template = request.template
    run_id = str(uuid.uuid4()) # Generate a unique ID for this crawl run

    # Initialize the job details in the in-memory dictionary
    crawl_jobs[run_id] = {
        'target_url': target_url,
        'template': template,
        'status': 'pending', # Initial status
        'progress': 0,
        'results': [],
        'started_at': time.time(), # Record start time
        'completed_at': None,
        'error_message': None, # Initialize error message
        'stats': {
            'total_pages_crawled': 0,
            'pages_indexed': 0,
            'pages_skipped': 0,
            'total_size_bytes': 0,
            'avg_page_size_bytes': 0,
            'crawl_duration_seconds': 0,
            'domains_found': set(),
            'file_types': {},
            'max_depth_reached': 0,
            'errors_encountered': 0
        }
    }

    # Add the crawl function to FastAPI's background tasks.
    # This allows the HTTP response to be sent instantly while the crawl runs.
    background_tasks.add_task(run_norconex_crawler_maven, run_id, target_url, request.template)

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

    # Convert sets to lists for JSON serialization
    stats = job.get('stats', {}).copy()
    if 'domains_found' in stats and isinstance(stats['domains_found'], set):
        stats['domains_found'] = list(stats['domains_found'])
    
    # Return the current status details of the job
    return JSONResponse(content={
        "run_id": run_id,
        "target_url": job['target_url'],
        "status": job['status'],
        "progress": job['progress'],
        "started_at": job['started_at'],
        "completed_at": job.get('completed_at'),
        "num_pages_indexed": len(job['results']), # Count of pages currently indexed
        "error_message": job.get('error_message'), # Get error message if exists
        "stats": stats
    })

@app.post("/crawl/stop/{run_id}")
async def stop_crawl(run_id: str):
    """
    Endpoint to stop a running crawl by its run_id.
    This will attempt to gracefully terminate the crawler process.
    """
    job = crawl_jobs.get(run_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Crawl run not found")
    
    if job['status'] not in ['running', 'pending']:
        raise HTTPException(status_code=409, detail=f"Cannot stop crawl in status: {job['status']}")
    
    try:
        stopped = False
        
        # Check if we have a direct process reference
        if run_id in running_processes and running_processes[run_id]:
            process = running_processes[run_id]
            if process.poll() is None:  # Process is still running
                print(f"[{run_id}] Terminating crawler process...")
                process.terminate()
                
                # Wait a few seconds for graceful shutdown
                try:
                    process.wait(timeout=10)
                    stopped = True
                    print(f"[{run_id}] Process terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    print(f"[{run_id}] Forcing process kill...")
                    process.kill()
                    process.wait()
                    stopped = True
                    print(f"[{run_id}] Process killed forcefully")
        
        # For Maven/container-based crawls, try HTTP stop request
        if not stopped:
            try:
                # Try to stop via HTTP API to norconex-maven container
                response = requests.post(
                    f"http://norconex-maven:8080/stop/{run_id}",
                    timeout=10
                )
                if response.status_code == 200:
                    stopped = True
                    print(f"[{run_id}] Stopped crawl via HTTP API")
                else:
                    print(f"[{run_id}] HTTP stop API returned: {response.status_code}")
            except Exception as e:
                logger.warning(f"[{run_id}] HTTP stop request failed: {e}")
        
        # For file-based triggers, create a stop signal file
        if not stopped:
            try:
                stop_file = f"/opt/norconex/configs/stop-{run_id}.json"
                stop_data = {
                    "run_id": run_id,
                    "action": "stop",
                    "timestamp": time.time()
                }
                
                with open(stop_file, 'w') as f:
                    import json
                    json.dump(stop_data, f)
                
                logger.info(f"[{run_id}] Created stop signal file: {stop_file}")
                stopped = True
            except Exception as e:
                print(f"[{run_id}] Failed to create stop file: {e}")
        
        # Update job status
        if stopped:
            crawl_jobs[run_id]['status'] = 'stopped'
            crawl_jobs[run_id]['completed_at'] = time.time()
            crawl_jobs[run_id]['progress'] = crawl_jobs[run_id].get('progress', 0)  # Keep current progress
            
            # Calculate duration
            duration = crawl_jobs[run_id]['completed_at'] - crawl_jobs[run_id]['started_at']
            crawl_jobs[run_id]['stats']['crawl_duration_seconds'] = round(duration, 2)
            
            # Clean up process tracking
            if run_id in running_processes:
                del running_processes[run_id]
            
            logger.info(f"[{run_id}] Crawl stopped successfully")
            
            return JSONResponse(content={
                "message": "Crawl stopped successfully",
                "run_id": run_id,
                "status": "stopped",
                "progress": crawl_jobs[run_id]['progress'],
                "duration": duration
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to stop crawl - no active process found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{run_id}] Error stopping crawl: {e}")
        raise HTTPException(status_code=500, detail=f"Error stopping crawl: {str(e)}")

@app.get("/results/{run_id}", response_model=list[PageRow])
async def get_crawl_results(run_id: str):
    """
    Endpoint to retrieve the indexed pages (results) for a specific crawl run.
    Results are returned if the crawl is complete or still running with partial data.
    Note: This endpoint is legacy - data is now in OpenSearch indexes (demo_factory_raw and demo_factory).
    """
    job = crawl_jobs.get(run_id)

    # If the run_id is not found, return a 404 error.
    if not job:
        raise HTTPException(status_code=404, detail="Crawl run not found")

    # Return the results if the crawl is complete, stopped, or still in progress (with partial results).
    # If it's pending or failed without results, return a 409 Conflict.
    if job['status'] in ['complete', 'running', 'stopped']:
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

@app.post("/crawl-logs/search")
async def search_crawl_logs_endpoint(request: CrawlLogSearchRequest):
    """
    Search crawl logs in OpenSearch.
    """
    try:
        results = search_crawl_logs(
            run_id=request.run_id,
            log_level=request.log_level,
            log_type=request.log_type,
            size=request.size
        )
        
        if "error" in results:
            raise HTTPException(status_code=500, detail=results["error"])
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawl log search error: {str(e)}")

@app.post("/crawl-logs/index/{run_id}")
async def index_crawl_logs_endpoint(run_id: str):
    """
    Manually trigger indexing of crawl logs for a specific run.
    """
    try:
        result = index_crawl_logs_to_opensearch(run_id)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Log indexing error: {str(e)}")

@app.post("/cms/detect")
async def detect_cms(request: CMSDetectionRequest):
    """
    Detect CMS/Platform of a given website URL.
    """
    try:
        detector = CMSDetector()
        result = detector.detect_cms(request.url)
        
        return {
            "success": True,
            "url": request.url,
            "detected_cms": result.get("detected_cms", "Unknown"),
            "confidence": result.get("confidence", 0),
            "details": result.get("details", {}),
            "detection_methods": result.get("detection_methods", []),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "success": False,
            "url": request.url,
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/cms/supported")
async def get_supported_cms():
    """
    Get list of supported CMS/Platforms for detection.
    """
    try:
        detector = CMSDetector()
        return {
            "success": True,
            "supported_cms": list(detector.cms_patterns.keys()),
            "total_count": len(detector.cms_patterns)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/crawl/list")
async def list_all_crawl_runs():
    """
    Get a list of all crawl runs with their current status, for frontend persistence.
    Returns both active and completed runs.
    """
    try:
        runs = []
        for run_id, job in crawl_jobs.items():
            run_data = {
                "run_id": run_id,
                "url": job.get("target_url", ""),
                "status": job.get("status", "unknown"),
                "progress": job.get("progress", 0),
                "started_at": job.get("started_at", 0),
                "completed_at": job.get("completed_at"),
                "template": job.get("template", "unknown"),
                "stats": job.get("stats", {})
            }

            # Add pages count from stats if available
            if "total_pages_crawled" in job.get("stats", {}):
                run_data["pages_crawled"] = job["stats"]["total_pages_crawled"]
            elif "pages_indexed" in job.get("stats", {}):
                run_data["pages_crawled"] = job["stats"]["pages_indexed"]
            else:
                run_data["pages_crawled"] = 0

            runs.append(run_data)

        # Sort by started_at timestamp, most recent first
        runs.sort(key=lambda x: x.get("started_at", 0), reverse=True)

        return {
            "runs": runs,
            "total": len(runs),
            "active_count": len([r for r in runs if r["status"] == "running"]),
            "completed_count": len([r for r in runs if r["status"] == "complete"])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list crawl runs: {str(e)}")


@app.post("/crawl/process/{run_id}")
async def process_crawl_to_schema(run_id: str):
    """
    Manually trigger schema processing for a crawl run.
    Note: Schema processing now runs automatically after each crawl.
    This endpoint is for re-processing or troubleshooting.
    Processes raw crawl data from demo_factory_raw into complete Search365 schema (229 fields) in demo_factory.
    """
    try:
        # Check if the run exists
        if run_id not in crawl_jobs:
            raise HTTPException(status_code=404, detail="Crawl run not found")

        # Check if the crawl is completed
        job = crawl_jobs[run_id]
        if job.get("status") != "complete":
            raise HTTPException(status_code=400, detail="Crawl must be completed before processing")

        processor = Search365SchemaProcessor()
        result = processor.process_crawl_to_main_index(run_id)

        if result.get("errors"):
            print(f"[{run_id}] Processing completed with errors: {result['errors']}")

        # Update job status with processing results
        crawl_jobs[run_id]["processing_result"] = result
        crawl_jobs[run_id]["processing_completed"] = True

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema processing error: {str(e)}")


@app.get("/crawl/{run_id}/raw")
async def get_raw_crawl_data(run_id: str):
    """
    Get raw crawl data from demo_factory_raw index (before schema enrichment).
    Returns first 10 documents as preview.
    """
    try:
        processor = Search365SchemaProcessor()
        raw_docs = processor._get_raw_crawl_documents(run_id)

        if not raw_docs:
            raise HTTPException(status_code=404, detail="Raw crawl data not found")

        return {
            "run_id": run_id,
            "document_count": len(raw_docs),
            "documents": raw_docs[:10],  # Return first 10 for preview
            "total_available": len(raw_docs)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving raw data: {str(e)}")


@app.websocket("/norconex/ws/{run_id}")
async def norconex_websocket(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for live Norconex crawl updates and backend logs"""
    await websocket.accept()

    # Add to connections list
    if run_id not in websocket_connections:
        websocket_connections[run_id] = []
    websocket_connections[run_id].append(websocket)

    try:
        # Send connection established message
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "run_id": run_id,
            "message": "Connected to Norconex crawl monitoring"
        }))

        # Send buffered logs for this run_id
        if run_id in log_buffer:
            logger.info(f"[WebSocket] Sending {len(log_buffer[run_id])} buffered logs for run_id {run_id[:8]}")
            for buffered_log in log_buffer[run_id]:
                await websocket.send_text(json.dumps({
                    "type": "backend_log",
                    "log": buffered_log
                }))

        # Send current crawl status if available
        if run_id in crawl_jobs:
            job = crawl_jobs[run_id]
            await websocket.send_text(json.dumps({
                "type": "status",
                "status": job["status"],
                "progress": job.get("progress", 0)
            }))

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong
            try:
                message = json.loads(data)
                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({'type': 'pong'}))
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        if run_id in websocket_connections:
            try:
                websocket_connections[run_id].remove(websocket)
            except ValueError:
                pass
    except Exception as e:
        print(f"WebSocket error for run_id {run_id}: {e}")
        if run_id in websocket_connections:
            try:
                websocket_connections[run_id].remove(websocket)
            except ValueError:
                pass


@app.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status and active runs"""
    return {
        "enabled": True,
        "active_runs": {run_id: len(connections) for run_id, connections in websocket_connections.items()},
        "total_connections": sum(len(connections) for connections in websocket_connections.values())
    }


