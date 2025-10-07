import os
import json
import requests
import re
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def index_crawl_logs_to_opensearch(run_id: str, opensearch_url: str = "http://opensearch:9200", index_name: str = "crawl_logs") -> Dict:
    """
    Index crawl logs from Norconex log files to OpenSearch.
    
    Args:
        run_id: The crawl run ID
        opensearch_url: OpenSearch endpoint URL
        index_name: Target index name for crawl logs
    
    Returns:
        Dict with indexing results
    """
    logger.info(f"Starting crawl log indexing for run {run_id}")
    
    # Define log file paths in norconex-runner
    trigger_log_path = "/opt/norconex/logs/trigger.log"
    runner_log_path = "/opt/norconex/logs/norconex-runner.log"
    
    # Fallback paths for development in norconex-runner
    if not os.path.exists(trigger_log_path):
        trigger_log_path = "./norconex-runner/logs/trigger.log"
    if not os.path.exists(runner_log_path):
        runner_log_path = "./norconex-runner/logs/norconex-runner.log"
    
    indexed_count = 0
    failed_count = 0
    errors = []
    
    try:
        # Create index if it doesn't exist
        create_crawl_logs_index(opensearch_url, index_name)
        
        # Index trigger log entries
        if os.path.exists(trigger_log_path):
            trigger_results = index_trigger_log_entries(run_id, trigger_log_path, opensearch_url, index_name)
            indexed_count += trigger_results.get('indexed', 0)
            failed_count += trigger_results.get('failed', 0)
            errors.extend(trigger_results.get('errors', []))
        
        # Index detailed crawler log entries
        if os.path.exists(runner_log_path):
            runner_results = index_runner_log_entries(run_id, runner_log_path, opensearch_url, index_name)
            indexed_count += runner_results.get('indexed', 0)
            failed_count += runner_results.get('failed', 0)
            errors.extend(runner_results.get('errors', []))
        
        result = {
            "indexed": indexed_count,
            "failed": failed_count,
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if errors:
            result["errors"] = errors[:10]  # Keep only first 10 errors
        
        logger.info(f"Crawl log indexing completed for {run_id}: {indexed_count} indexed, {failed_count} failed")
        return result
        
    except Exception as e:
        error_msg = f"Error indexing crawl logs for {run_id}: {str(e)}"
        logger.error(error_msg)
        return {"indexed": 0, "failed": 0, "error": error_msg}

def create_crawl_logs_index(opensearch_url: str, index_name: str) -> bool:
    """
    Create the crawl logs index with proper mapping if it doesn't exist.
    """
    try:
        # Check if index exists
        response = requests.head(f"{opensearch_url}/{index_name}")
        if response.status_code == 200:
            return True  # Index already exists
        
        # Create index with mapping
        mapping = {
            "mappings": {
                "properties": {
                    "run_id": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "log_level": {"type": "keyword"},
                    "logger": {"type": "keyword"},
                    "message": {"type": "text"},
                    "log_type": {"type": "keyword"},  # "trigger", "runner", "execution_summary"
                    "thread": {"type": "keyword"},
                    "execution_stats": {
                        "properties": {
                            "total_processed": {"type": "integer"},
                            "crawl_duration": {"type": "keyword"},
                            "avg_throughput": {"type": "float"},
                            "event_counts": {"type": "object"}
                        }
                    },
                    "raw_log_line": {"type": "text"}
                }
            }
        }
        
        response = requests.put(
            f"{opensearch_url}/{index_name}",
            json=mapping,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        logger.error(f"Error creating crawl logs index: {e}")
        return False

def index_trigger_log_entries(run_id: str, log_path: str, opensearch_url: str, index_name: str) -> Dict:
    """
    Parse and index trigger log entries for a specific run.
    """
    indexed_count = 0
    failed_count = 0
    errors = []
    
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line or run_id not in line:
                continue
            
            # Parse trigger log line
            log_entry = parse_trigger_log_line(line, run_id)
            if log_entry:
                success = index_log_entry(log_entry, opensearch_url, index_name)
                if success:
                    indexed_count += 1
                else:
                    failed_count += 1
                    
    except Exception as e:
        error_msg = f"Error processing trigger log: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    
    return {"indexed": indexed_count, "failed": failed_count, "errors": errors}

def index_runner_log_entries(run_id: str, log_path: str, opensearch_url: str, index_name: str) -> Dict:
    """
    Parse and index runner log entries for a specific run.
    """
    indexed_count = 0
    failed_count = 0
    errors = []
    
    try:
        with open(log_path, 'r') as f:
            content = f.read()
        
        # Find execution summary for this run
        summary_match = find_execution_summary_for_run(content, run_id)
        if summary_match:
            log_entry = parse_execution_summary(summary_match, run_id)
            if log_entry:
                success = index_log_entry(log_entry, opensearch_url, index_name)
                if success:
                    indexed_count += 1
                else:
                    failed_count += 1
        
        # Index other relevant log lines for this run
        lines = content.split('\n')
        for line in lines:
            if not line.strip():
                continue
            
            # Look for log lines that might be related to our run
            # This is a heuristic based on timing and context
            log_entry = parse_runner_log_line(line.strip(), run_id)
            if log_entry:
                success = index_log_entry(log_entry, opensearch_url, index_name)
                if success:
                    indexed_count += 1
                else:
                    failed_count += 1
                    
    except Exception as e:
        error_msg = f"Error processing runner log: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    
    return {"indexed": indexed_count, "failed": failed_count, "errors": errors}

def parse_trigger_log_line(line: str, run_id: str) -> Optional[Dict]:
    """
    Parse a trigger log line into a structured log entry.
    """
    try:
        # Example: Mon Aug 25 07:20:35 UTC 2025: Found trigger file: /opt/norconex/configs/trigger-{run_id}.json
        timestamp_match = re.match(r'^(\w+ \w+ \d+ \d+:\d+:\d+ \w+ \d+):\s*(.+)$', line)
        if not timestamp_match:
            return None
        
        timestamp_str = timestamp_match.group(1)
        message = timestamp_match.group(2)
        
        # Convert timestamp to ISO format
        try:
            timestamp = datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S %Z %Y')
            iso_timestamp = timestamp.isoformat() + 'Z'
        except:
            iso_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        return {
            "run_id": run_id,
            "timestamp": iso_timestamp,
            "log_level": "INFO",
            "logger": "trigger",
            "message": message,
            "log_type": "trigger",
            "raw_log_line": line
        }
        
    except Exception as e:
        logger.error(f"Error parsing trigger log line: {e}")
        return None

def parse_runner_log_line(line: str, run_id: str) -> Optional[Dict]:
    """
    Parse a runner log line into a structured log entry.
    """
    try:
        # Example: 2025-08-24 17:24:00.109 [main] INFO  io.demo.nx.Runner - Norconex Runner starting with 0 arguments
        log_pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+\[([^\]]+)\]\s+(\w+)\s+([^\s]+)\s+-\s+(.+)$'
        match = re.match(log_pattern, line)
        
        if not match:
            return None
        
        timestamp_str = match.group(1)
        thread = match.group(2)
        log_level = match.group(3)
        logger_name = match.group(4)
        message = match.group(5)
        
        # Convert timestamp to ISO format
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
            iso_timestamp = timestamp.isoformat() + 'Z'
        except:
            iso_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        return {
            "run_id": run_id,
            "timestamp": iso_timestamp,
            "log_level": log_level,
            "logger": logger_name,
            "message": message,
            "log_type": "runner",
            "thread": thread,
            "raw_log_line": line
        }
        
    except Exception as e:
        logger.error(f"Error parsing runner log line: {e}")
        return None

def find_execution_summary_for_run(content: str, run_id: str) -> Optional[str]:
    """
    Find the execution summary section for a specific run.
    """
    try:
        # Look for completion marker for this run
        run_pattern = rf'Crawl (?:completed successfully|failed) for {re.escape(run_id)}'
        run_match = re.search(run_pattern, content)
        
        if not run_match:
            return None
        
        # Work backwards from the completion marker to find the execution summary
        content_before = content[:run_match.start()]
        
        # Look for the most recent execution summary before this completion  
        summary_pattern = r'Execution Summary:\s*\nTotal processed:\s*(\d+)\s*\nSince.*?\n\s*Crawl duration:\s*([^\n]+)\n\s*Avg\. throughput:\s*([^\n]+)\n\s*Event counts:\s*\n((?:\s*[A-Z_]+:\s*\d+\s*\n)*)'
        
        matches = list(re.finditer(summary_pattern, content_before, re.MULTILINE | re.DOTALL))
        if not matches:
            return None
        
        # Return the most recent execution summary
        return matches[-1].group(0)
        
    except Exception as e:
        logger.error(f"Error finding execution summary: {e}")
        return None

def parse_execution_summary(summary_text: str, run_id: str) -> Optional[Dict]:
    """
    Parse execution summary into a structured log entry.
    """
    try:
        # Extract summary data
        total_match = re.search(r'Total processed:\s*(\d+)', summary_text)
        duration_match = re.search(r'Crawl duration:\s*([^\n]+)', summary_text)
        throughput_match = re.search(r'Avg\. throughput:\s*([^\n]+)', summary_text)
        events_match = re.search(r'Event counts:\s*\n((?:\s*[A-Z_]+:\s*\d+\s*\n)*)', summary_text, re.MULTILINE)
        
        execution_stats = {}
        
        if total_match:
            execution_stats['total_processed'] = int(total_match.group(1))
        
        if duration_match:
            execution_stats['crawl_duration'] = duration_match.group(1).strip()
        
        if throughput_match:
            throughput_str = throughput_match.group(1).strip()
            throughput_num_match = re.search(r'([0-9.]+)\s+processed/seconds', throughput_str)
            if throughput_num_match:
                execution_stats['avg_throughput'] = float(throughput_num_match.group(1))
        
        if events_match:
            events_section = events_match.group(1)
            event_counts = {}
            for line in events_section.split('\n'):
                line = line.strip()
                if line:
                    event_match = re.match(r'([A-Z_]+):\s*(\d+)', line)
                    if event_match:
                        event_counts[event_match.group(1)] = int(event_match.group(2))
            execution_stats['event_counts'] = event_counts
        
        return {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "log_level": "INFO",
            "logger": "execution_summary",
            "message": "Crawl execution summary",
            "log_type": "execution_summary",
            "execution_stats": execution_stats,
            "raw_log_line": summary_text
        }
        
    except Exception as e:
        logger.error(f"Error parsing execution summary: {e}")
        return None

def index_log_entry(log_entry: Dict, opensearch_url: str, index_name: str) -> bool:
    """
    Index a single log entry to OpenSearch.
    """
    try:
        # Generate document ID
        doc_id = f"{log_entry['run_id']}_{log_entry['timestamp']}_{log_entry['log_type']}"
        doc_id = doc_id.replace(':', '_').replace('.', '_').replace('+', '_')
        
        response = requests.post(
            f'{opensearch_url}/{index_name}/_doc/{doc_id}',
            headers={'Content-Type': 'application/json'},
            json=log_entry,
            timeout=30
        )
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        logger.error(f"Error indexing log entry to OpenSearch: {e}")
        return False

def search_crawl_logs(run_id: str = None, log_level: str = None, log_type: str = None, 
                     opensearch_url: str = "http://opensearch:9200", index_name: str = "crawl_logs", 
                     size: int = 100) -> Dict:
    """
    Search crawl logs in OpenSearch.
    
    Args:
        run_id: Filter by specific run ID
        log_level: Filter by log level (INFO, ERROR, etc.)
        log_type: Filter by log type (trigger, runner, execution_summary)
        opensearch_url: OpenSearch endpoint URL
        index_name: Index name to search
        size: Number of results to return
    
    Returns:
        Search results
    """
    try:
        query = {"match_all": {}}
        filters = []
        
        if run_id:
            filters.append({"term": {"run_id": run_id}})
        if log_level:
            filters.append({"term": {"log_level": log_level}})
        if log_type:
            filters.append({"term": {"log_type": log_type}})
        
        if filters:
            query = {
                "bool": {
                    "must": filters
                }
            }
        
        search_body = {
            "size": size,
            "query": query,
            "sort": [{"timestamp": {"order": "desc"}}]
        }
        
        response = requests.post(
            f"{opensearch_url}/{index_name}/_search",
            json=search_body,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code != 200:
            return {"error": f"OpenSearch error: {response.text}"}
        
        search_results = response.json()
        
        logs = []
        for hit in search_results["hits"]["hits"]:
            logs.append(hit["_source"])
        
        return {
            "total": search_results["hits"]["total"]["value"],
            "logs": logs
        }
        
    except Exception as e:
        return {"error": f"Search error: {str(e)}"}