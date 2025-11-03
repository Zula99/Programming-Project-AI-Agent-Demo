"""
Task Manager for AsyncIO Background Tasks

Manages running crawl tasks with clean cancellation support.
"""

import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages background AsyncIO tasks for crawl sessions"""

    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.stop_flags: Dict[str, bool] = {}  # Simple stop flags

    def register_task(self, run_id: str, task: asyncio.Task):
        """Register a running task"""
        self.tasks[run_id] = task
        self.stop_flags[run_id] = False  # Initialize as not stopped
        logger.debug(f"Registered task for run_id: {run_id}")

    def should_stop(self, run_id: str) -> bool:
        """Check if task should stop"""
        return self.stop_flags.get(run_id, False)

    def get_task(self, run_id: str) -> Optional[asyncio.Task]:
        """Get task for a run_id"""
        return self.tasks.get(run_id)

    async def cancel_task(self, run_id: str) -> bool:
        """
        Force cancel a running task immediately.

        Returns:
            True if task was cancelled, False if task not found or already done
        """
        # Set stop flag FIRST - this gets checked in loops
        self.stop_flags[run_id] = True
        logger.info(f"FORCE STOP: Stop flag set for run_id: {run_id}")

        task = self.tasks.get(run_id)

        if not task:
            logger.warning(f"No task found for run_id: {run_id}")
            return True  # Still return True since we set the flag

        if task.done():
            logger.info(f"Task for run_id {run_id} already completed")
            self.cleanup_task(run_id)
            return True

        # Also cancel the asyncio task
        task.cancel()
        logger.info(f"FORCE STOP: Asyncio task cancelled for run_id: {run_id}")

        return True

    def cleanup_task(self, run_id: str):
        """Remove task from tracking"""
        if run_id in self.tasks:
            del self.tasks[run_id]
        if run_id in self.stop_flags:
            del self.stop_flags[run_id]
        logger.debug(f"Cleaned up task for run_id: {run_id}")

    def is_running(self, run_id: str) -> bool:
        """Check if task is currently running"""
        task = self.tasks.get(run_id)
        return task is not None and not task.done()

    def get_running_count(self) -> int:
        """Get count of currently running tasks"""
        return sum(1 for task in self.tasks.values() if not task.done())


# Global task manager instance
task_manager = TaskManager()
