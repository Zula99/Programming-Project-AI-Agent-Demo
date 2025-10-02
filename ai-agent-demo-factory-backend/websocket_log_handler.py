"""
WebSocket Log Handler
Broadcasts all logging statements to connected WebSocket clients and OpenSearch
"""

import logging
import asyncio
import json
import time
import sys
from typing import Dict, List, Optional
from fastapi import WebSocket
from contextvars import ContextVar

# Import OpenSearch logging
sys.path.append("./crawl4ai-agent")
from opensearch_logger import log_to_opensearch

# Global registry of WebSocket connections per run_id
websocket_connections: Dict[str, List[WebSocket]] = {}

# Context variable to track current run_id
current_run_id: ContextVar[Optional[str]] = ContextVar('current_run_id', default=None)


class WebSocketLogHandler(logging.Handler):
    """
    Custom logging handler that broadcasts logs to WebSocket clients and OpenSearch

    Features:
    - Real-time log broadcasting to all connected WebSocket clients
    - Async OpenSearch indexing for persistent searchable logs
    - Automatic filtering of infrastructure noise logs
    """

    def __init__(self, enable_opensearch=True):
        super().__init__()
        self.setLevel(logging.DEBUG)
        self.enable_opensearch = enable_opensearch

    def emit(self, record):
        try:
            # Skip DEBUG logs - only show INFO, WARNING, ERROR, CRITICAL
            if record.levelno < logging.INFO:
                return

            # Skip spammy OpenSearch operational logs
            if 'opensearch' in record.name or 'opensearch_integration' in record.name:
                message = record.getMessage()
                skip_patterns = [
                    'POST http://', 'GET http://', 'HEAD http://',
                    'Connected to OpenSearch cluster',
                    'Log index', 'already exists'
                ]
                if any(pattern in message for pattern in skip_patterns):
                    return

            # Format the log message for WebSocket
            backend_log = {
                "timestamp": time.strftime("%H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "source": record.name,
                "message": record.getMessage()
            }

            # Broadcast to all WebSocket connections (existing functionality)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(broadcast_backend_log(backend_log))
            except RuntimeError:
                # No event loop running - skip WebSocket broadcast
                pass

            # Also send to OpenSearch (new functionality)
            if self.enable_opensearch:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._send_to_opensearch(record))
                except RuntimeError:
                    # No event loop running - skip OpenSearch logging
                    pass

        except Exception:
            pass  # Don't let logging errors crash the app

    async def _send_to_opensearch(self, record):
        """Send log entry to OpenSearch asynchronously"""
        try:
            # Skip OpenSearch's own logs to prevent feedback loop
            if any(skip_logger in record.name for skip_logger in [
                'opensearch', 'urllib3', 'opensearch_integration'
            ]):
                return

            # Get run_id from context
            run_id = current_run_id.get()
            if not run_id:
                # Skip logging if no run_id context (startup logs, etc.)
                return

            # Extract metadata from record if available
            metadata = {}
            if hasattr(record, 'extra_data'):
                metadata = record.extra_data

            # Add contextual information including run_id
            metadata.update({
                "run_id": run_id,
                "thread_id": str(record.thread),
                "pathname": record.pathname,
                "lineno": record.lineno,
                "funcName": record.funcName
            })

            # Use the existing log_to_opensearch function with run_id-based index
            log_to_opensearch(
                service="fastapi-backend",
                component=record.name.split('.')[-1] if '.' in record.name else record.name,
                level=record.levelname,
                message=record.getMessage(),
                metadata=metadata,
                run_id=run_id  # Pass run_id for index naming
            )
        except Exception:
            # Fail silently to not disrupt main application
            pass


async def broadcast_backend_log(backend_log):
    """Broadcast log message to all connected WebSocket clients"""
    message = {
        "type": "backend_log",
        "log": backend_log
    }

    for run_id, connections in websocket_connections.items():
        for websocket in connections[:]:  # Use slice to avoid modification during iteration
            try:
                await websocket.send_text(json.dumps(message))
                # Small yield to allow other tasks to run and WebSocket to actually send
                await asyncio.sleep(0)
            except:
                # Remove disconnected websockets
                connections.remove(websocket)


def setup_websocket_logging():
    """
    Configure logging to broadcast to WebSocket clients and OpenSearch

    Call this once at application startup to:
    - Create WebSocketLogHandler
    - Attach to root logger (captures all modules)
    - Attach to uvicorn logger (FastAPI server logs)
    """
    # Create handler
    websocket_handler = WebSocketLogHandler()
    websocket_handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))

    # Configure root logger to capture all logs (INFO and above)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(websocket_handler)

    # Silence noisy third-party DEBUG logs
    logging.getLogger("opensearch").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Configure uvicorn logger specifically
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.addHandler(websocket_handler)

    return websocket_handler