"""
WebSocket Manager - Real-time coverage updates for frontend dashboards

Handles WebSocket connections and broadcasts real-time crawling progress
to connected frontend clients. Keeps connection management separate from
crawler logic for clean separation of concerns.

US-53: Real-time coverage monitoring via WebSocket
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import asdict

from dashboard_metrics import CoverageSnapshot, get_coverage_calculator


class WebSocketConnectionManager:
    """Manages WebSocket connections for real-time coverage updates"""
    
    def __init__(self):
        # Active connections per run_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket, run_id: str):
        """Accept new WebSocket connection for specific run_id"""
        await websocket.accept()
        
        if run_id not in self.active_connections:
            self.active_connections[run_id] = set()
        
        self.active_connections[run_id].add(websocket)
        self.logger.info(f"WebSocket connected for run_id: {run_id} (total: {len(self.active_connections[run_id])})")
        
        # Send initial coverage data if available
        await self._send_initial_data(websocket, run_id)
    
    def disconnect(self, websocket: WebSocket, run_id: str):
        """Handle WebSocket disconnection"""
        if run_id in self.active_connections:
            self.active_connections[run_id].discard(websocket)
            
            # Clean up empty connection sets
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
        
        self.logger.info(f"WebSocket disconnected for run_id: {run_id}")
    
    async def _send_initial_data(self, websocket: WebSocket, run_id: str):
        """Send current coverage state to newly connected client"""
        try:
            calculator = get_coverage_calculator(run_id)
            if calculator:
                snapshot = calculator.get_current_snapshot()
                await websocket.send_text(json.dumps({
                    'type': 'coverage_update',
                    'data': asdict(snapshot)
                }))
                self.logger.debug(f"Sent initial coverage data for run_id: {run_id}")
        except Exception as e:
            self.logger.error(f"Failed to send initial data for {run_id}: {e}")
    
    async def broadcast_coverage_update(self, run_id: str, snapshot: CoverageSnapshot):
        """Broadcast coverage update to all connected clients for this run_id"""
        if run_id not in self.active_connections:
            return
        
        message = json.dumps({
            'type': 'coverage_update',
            'data': asdict(snapshot)
        })
        
        # Send to all connected clients
        disconnected_websockets = set()
        
        for websocket in self.active_connections[run_id].copy():
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                disconnected_websockets.add(websocket)
            except Exception as e:
                self.logger.error(f"Error sending to WebSocket: {e}")
                disconnected_websockets.add(websocket)
        
        # Clean up disconnected WebSockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket, run_id)
        
        if len(self.active_connections.get(run_id, [])) > 0:
            self.logger.debug(f"Broadcasted coverage update to {len(self.active_connections[run_id])} clients for run_id: {run_id}")
    
    async def broadcast_crawl_event(self, run_id: str, event_type: str, data: Dict[str, Any]):
        """Broadcast general crawl events (start, stop, error, etc.)"""
        if run_id not in self.active_connections:
            return
        
        message = json.dumps({
            'type': event_type,
            'run_id': run_id,
            'timestamp': asyncio.get_event_loop().time(),
            'data': data
        })
        
        disconnected_websockets = set()
        
        for websocket in self.active_connections[run_id].copy():
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                disconnected_websockets.add(websocket)
            except Exception as e:
                self.logger.error(f"Error sending event to WebSocket: {e}")
                disconnected_websockets.add(websocket)
        
        # Clean up disconnected WebSockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket, run_id)
        
        self.logger.info(f"Broadcasted {event_type} event for run_id: {run_id}")
    
    async def send_quality_plateau_alert(self, run_id: str, plateau_info: Dict[str, Any]):
        """Send quality plateau detection alert"""
        await self.broadcast_crawl_event(run_id, 'quality_plateau_detected', plateau_info)
    
    async def send_crawl_completion(self, run_id: str, final_stats: Dict[str, Any]):
        """Send crawl completion notification"""
        await self.broadcast_crawl_event(run_id, 'crawl_completed', final_stats)
    
    async def send_error_notification(self, run_id: str, error_info: Dict[str, Any]):
        """Send error notification"""
        await self.broadcast_crawl_event(run_id, 'crawl_error', error_info)
    
    def get_connection_count(self, run_id: str) -> int:
        """Get number of active connections for run_id"""
        return len(self.active_connections.get(run_id, []))
    
    def get_all_active_runs(self) -> Dict[str, int]:
        """Get all active run_ids and their connection counts"""
        return {run_id: len(connections) for run_id, connections in self.active_connections.items()}
    
    async def cleanup_run(self, run_id: str):
        """Clean up all connections for completed run"""
        if run_id in self.active_connections:
            # Send final notification
            await self.broadcast_crawl_event(run_id, 'run_cleanup', {'message': 'Crawl monitoring ended'})
            
            # Close all connections
            for websocket in self.active_connections[run_id].copy():
                try:
                    await websocket.close()
                except Exception as e:
                    self.logger.debug(f"Error closing WebSocket: {e}")
            
            del self.active_connections[run_id]
            self.logger.info(f"Cleaned up all WebSocket connections for run_id: {run_id}")


# Global WebSocket manager instance
websocket_manager = WebSocketConnectionManager()


# Convenience functions for crawler integration
async def broadcast_coverage_update(run_id: str):
    """Convenience function to broadcast current coverage state"""
    calculator = get_coverage_calculator(run_id)
    if calculator:
        snapshot = calculator.get_current_snapshot()
        await websocket_manager.broadcast_coverage_update(run_id, snapshot)


async def notify_crawl_start(run_id: str, start_info: Dict[str, Any]):
    """Notify that crawl has started"""
    await websocket_manager.broadcast_crawl_event(run_id, 'crawl_started', start_info)


async def notify_crawl_complete(run_id: str, final_stats: Dict[str, Any]):
    """Notify that crawl has completed"""
    await websocket_manager.send_crawl_completion(run_id, final_stats)


async def notify_quality_plateau(run_id: str, plateau_info: Dict[str, Any]):
    """Notify quality plateau detection"""
    await websocket_manager.send_quality_plateau_alert(run_id, plateau_info)


async def notify_page_crawled(run_id: str, url: str, success: bool, quality_score: Optional[float] = None):
    """Notify that a page has been crawled and broadcast updated coverage"""
    calculator = get_coverage_calculator(run_id)
    if calculator:
        calculator.mark_url_crawled(url, success, quality_score)
        await broadcast_coverage_update(run_id)


async def notify_urls_discovered(run_id: str, new_urls: list):
    """Notify that new URLs have been discovered"""
    calculator = get_coverage_calculator(run_id)
    if calculator:
        calculator.add_discovered_urls(new_urls)
        await broadcast_coverage_update(run_id)


async def cleanup_websocket_connections(run_id: str):
    """Clean up WebSocket connections when crawl ends"""
    await websocket_manager.cleanup_run(run_id)