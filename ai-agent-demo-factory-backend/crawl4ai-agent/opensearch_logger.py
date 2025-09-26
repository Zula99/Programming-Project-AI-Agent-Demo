"""
OpenSearch Logger Integration

Extends the existing CrawlLogger to also send logs to OpenSearch
for real-time monitoring and searchability while keeping file-based logging.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import threading
import queue
import time

# Import existing logger and OpenSearch integration
from crawl_logger import CrawlLogger, CrawlSession
sys.path.append(str(Path(__file__).parent.parent / "Utility"))
from opensearch_integration import Crawl4AIOpenSearchIntegration, OpenSearchConfig


class OpenSearchLogHandler(logging.Handler):
    """
    Custom logging handler that sends logs to OpenSearch
    Works asynchronously to not block the main process
    """

    def __init__(self, opensearch_integration: Crawl4AIOpenSearchIntegration,
                 index_name: str, service_name: str):
        super().__init__()
        self.opensearch = opensearch_integration
        self.index_name = index_name
        self.service_name = service_name

        # Async queue for non-blocking log processing
        self.log_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_logs, daemon=True)
        self.worker_thread.start()

    def emit(self, record):
        """Add log record to queue for async processing"""
        try:
            log_entry = self._format_log_entry(record)
            self.log_queue.put(log_entry)
        except Exception:
            # Don't let logging errors break the main process
            pass

    def _format_log_entry(self, record) -> Dict[str, Any]:
        """Convert LogRecord to OpenSearch document format"""
        # Extract metadata from record if available
        metadata = {}
        if hasattr(record, 'extra_data') and record.extra_data:
            metadata = record.extra_data

        return {
            "@timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "component": record.name.split('.')[-1] if '.' in record.name else record.name,
            "message": record.getMessage(),
            "metadata": metadata,
            "thread_id": str(record.thread),
            "process_id": str(record.process) if hasattr(record, 'process') else None,
            "pathname": record.pathname,
            "lineno": record.lineno
        }

    def _process_logs(self):
        """Background worker to process log queue"""
        batch = []
        last_flush = time.time()

        while True:
            try:
                # Get log entry with timeout
                try:
                    log_entry = self.log_queue.get(timeout=1.0)
                    batch.append(log_entry)
                except queue.Empty:
                    pass

                # Flush batch if it's full or enough time has passed
                current_time = time.time()
                should_flush = (
                    len(batch) >= 10 or  # Batch size limit
                    (batch and current_time - last_flush > 5.0)  # Time limit
                )

                if should_flush and batch:
                    self.opensearch.bulk_index_logs(batch, self.index_name)
                    batch = []
                    last_flush = current_time

            except Exception:
                # Continue processing even if some logs fail
                batch = []
                continue


class OpenSearchCrawlLogger(CrawlLogger):
    """
    Enhanced CrawlLogger that also sends logs to OpenSearch

    Maintains all existing functionality while adding OpenSearch integration
    """

    def __init__(self, base_url: str, output_dir: str = "./output/logs",
                 opensearch_config: OpenSearchConfig = None,
                 enable_opensearch: bool = True):
        # Initialize parent class
        super().__init__(base_url, output_dir)

        # OpenSearch integration
        self.enable_opensearch = enable_opensearch
        self.opensearch_integration = None
        self.opensearch_handler = None

        if enable_opensearch:
            try:
                self.opensearch_integration = Crawl4AIOpenSearchIntegration(opensearch_config)
                # Create monthly index name
                index_name = f"ai-agent-logs-{datetime.now().strftime('%Y.%m')}"
                self.opensearch_handler = OpenSearchLogHandler(
                    self.opensearch_integration,
                    index_name,
                    "smart-mirror-agent"
                )
            except Exception as e:
                print(f"Warning: OpenSearch logging disabled - {e}")
                self.enable_opensearch = False

    def start_logging(self):
        """Start both file and OpenSearch logging"""
        # Call parent method for file logging
        super().start_logging()

        # Add OpenSearch handler to logger
        if self.enable_opensearch and self.opensearch_handler:
            self.logger.addHandler(self.opensearch_handler)
            self.logger.info("OpenSearch logging enabled", extra={'extra_data': {
                'opensearch_enabled': True,
                'domain': self.domain
            }})

    def log_phase(self, phase_name: str, details: str = ""):
        """Log phase with OpenSearch metadata"""
        if self.logger:
            self.logger.info(f"PHASE: {phase_name} - {details}", extra={'extra_data': {
                'phase': phase_name,
                'phase_details': details,
                'domain': self.domain,
                'log_type': 'phase'
            }})
            print(f"📊 {phase_name}: {details}")

    def log_error(self, error: Exception, context: str = ""):
        """Log error with OpenSearch metadata"""
        if self.logger:
            self.logger.error(f"ERROR in {context}: {str(error)}", extra={'extra_data': {
                'error_type': type(error).__name__,
                'error_context': context,
                'domain': self.domain,
                'log_type': 'error'
            }})
            self.logger.error(f"Error type: {type(error).__name__}")

    def log_metrics(self, metrics: dict):
        """Log metrics with OpenSearch metadata"""
        if self.logger:
            self.logger.info("QUALITY METRICS:", extra={'extra_data': {
                'metrics': metrics,
                'domain': self.domain,
                'log_type': 'metrics'
            }})
            for key, value in metrics.items():
                self.logger.info(f"  {key}: {value}")

    def log_ai_classification(self, url: str, classification: str, confidence: float, cost: float):
        """Special method for AI classification logging"""
        if self.logger:
            self.logger.info(f"AI Classification: {url} -> {classification} (confidence: {confidence:.2f})",
                           extra={'extra_data': {
                'url': url,
                'ai_classification': classification,
                'ai_confidence': confidence,
                'cost_usd': cost,
                'domain': self.domain,
                'log_type': 'ai_classification'
            }})

    def stop_logging(self, success: bool = True, final_message: str = ""):
        """Stop both file and OpenSearch logging"""
        # Log final status to OpenSearch
        if self.logger and self.enable_opensearch:
            duration = time.time() - self.start_time if self.start_time else 0
            self.logger.info(f"Crawl session ended: {'SUCCESS' if success else 'FAILED'}",
                           extra={'extra_data': {
                'success': success,
                'duration_seconds': duration,
                'final_message': final_message,
                'domain': self.domain,
                'log_type': 'session_end'
            }})

        # Call parent method
        super().stop_logging(success, final_message)


class OpenSearchCrawlSession(CrawlSession):
    """Context manager for OpenSearch-enabled crawl logging"""

    def __init__(self, base_url: str, output_dir: str = "./output/logs",
                 opensearch_config: OpenSearchConfig = None):
        # Override the logger creation
        self.logger = OpenSearchCrawlLogger(base_url, output_dir, opensearch_config)
        self.success = False


# Simple usage functions
def create_opensearch_logger(base_url: str, enable_opensearch: bool = True) -> OpenSearchCrawlLogger:
    """Create an OpenSearch-enabled logger"""
    return OpenSearchCrawlLogger(base_url, enable_opensearch=enable_opensearch)


def log_to_opensearch(service: str, component: str, level: str, message: str,
                     metadata: Dict[str, Any] = None):
    """Simple function to send a single log entry to OpenSearch"""
    try:
        opensearch = Crawl4AIOpenSearchIntegration()
        index_name = f"ai-agent-logs-{datetime.now().strftime('%Y.%m')}"

        log_entry = {
            "@timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "service": service,
            "component": component,
            "message": message,
            "metadata": metadata or {}
        }

        opensearch.index_log_entry(log_entry, index_name)
        return True
    except Exception:
        return False