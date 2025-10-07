"""
Norconex WebSocket Log Handler
Broadcasts all logging statements to connected WebSocket clients

Captures all backend logs (FastAPI, Norconex runner, etc.) and streams
them to frontend clients via WebSocket for real-time monitoring.
"""

import logging
import asyncio
import json
import time
from typing import Dict, List
from fastapi import WebSocket
from contextvars import ContextVar

# Global registry of WebSocket connections per run_id
websocket_connections: Dict[str, List[WebSocket]] = {}

# Buffer of recent logs per run_id (kept for 5 minutes)
log_buffer: Dict[str, List[Dict]] = {}
LOG_BUFFER_SIZE = 100  # Keep last 100 logs per run

# Context variable to track current run_id
current_run_id: ContextVar[str | None] = ContextVar('current_run_id', default=None)


class WebSocketLogHandler(logging.Handler):
    """
    Custom logging handler that broadcasts logs to WebSocket clients

    Features:
    - Real-time log broadcasting to all connected WebSocket clients
    - Automatic filtering of infrastructure noise logs
    - Per-run_id connection tracking
    """

    def __init__(self):
        super().__init__()
        self.setLevel(logging.DEBUG)

    def emit(self, record):
        try:
            # Skip DEBUG logs - only show INFO, WARNING, ERROR, CRITICAL
            if record.levelno < logging.INFO:
                return

            # Skip spammy infrastructure logs
            if any(skip_logger in record.name for skip_logger in [
                'urllib3', 'asyncio', 'watchfiles', 'httpcore', 'httpx'
            ]):
                return

            # Format the log message for WebSocket
            backend_log = {
                "timestamp": time.strftime("%H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "source": record.name,
                "message": record.getMessage()
            }

            # Broadcast to all WebSocket connections
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(broadcast_backend_log(backend_log))
            except RuntimeError as e:
                # No event loop running - skip WebSocket broadcast
                print(f"[WebSocket] No event loop available for broadcasting: {e}")
                pass

        except Exception:
            pass  # Don't let logging errors crash the app


async def broadcast_backend_log(backend_log):
    """Broadcast log message to relevant WebSocket clients based on run_id"""
    message = {
        "type": "backend_log",
        "log": backend_log
    }

    # Extract run_id from log message if present
    log_msg = backend_log['message']
    run_id_match = None
    if log_msg.startswith('[') and ']' in log_msg:
        run_id_match = log_msg[1:log_msg.index(']')]

    # Buffer the log for this run_id
    if run_id_match:
        if run_id_match not in log_buffer:
            log_buffer[run_id_match] = []
        log_buffer[run_id_match].append(backend_log)
        # Keep only the last LOG_BUFFER_SIZE logs
        if len(log_buffer[run_id_match]) > LOG_BUFFER_SIZE:
            log_buffer[run_id_match] = log_buffer[run_id_match][-LOG_BUFFER_SIZE:]

    # Only send to connections for the matching run_id
    if run_id_match and run_id_match in websocket_connections:
        connections = websocket_connections[run_id_match]
        print(f"[WebSocket] Broadcasting to {len(connections)} connections for run_id {run_id_match[:8]}: {backend_log['message'][:50]}")

        for websocket in connections[:]:  # Use slice to avoid modification during iteration
            try:
                await websocket.send_text(json.dumps(message))
                print(f"[WebSocket] Sent to run_id {run_id_match[:8]}")
                # Small yield to allow other tasks to run
                await asyncio.sleep(0)
            except Exception as e:
                print(f"[WebSocket] Failed to send to {run_id_match[:8]}: {e}")
                # Remove disconnected websockets
                try:
                    connections.remove(websocket)
                except ValueError:
                    pass  # Already removed
    else:
        # Log without run_id - skip broadcasting or broadcast to all
        connection_count = sum(len(conns) for conns in websocket_connections.values())
        print(f"[WebSocket] Skipping broadcast of log without run_id to {connection_count} connections: {backend_log['message'][:50]}")


def setup_websocket_logging():
    """
    Configure logging to broadcast to WebSocket clients

    Call this once at application startup to:
    - Create WebSocketLogHandler
    - Attach to root logger (captures all modules)
    - Attach to uvicorn logger (FastAPI server logs)
    """
    # Create handler
    websocket_handler = WebSocketLogHandler()
    websocket_handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))

    # Also create console handler for debugging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))

    # Configure root logger to capture all logs (INFO and above)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(websocket_handler)
    root_logger.addHandler(console_handler)

    # Silence noisy third-party DEBUG logs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    # Configure uvicorn logger specifically
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.addHandler(websocket_handler)

    return websocket_handler
