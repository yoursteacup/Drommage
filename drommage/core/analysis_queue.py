"""
Asynchronous analysis queue - handles LLM analysis without blocking UI
"""

import threading
import queue
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum

from .llm_analyzer import LLMAnalyzer, AnalysisLevel, DiffAnalysis

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class AnalysisTask:
    """Analysis task for the queue"""
    id: str
    old_text: str
    new_text: str
    context: str
    level: AnalysisLevel
    callback: Callable[[DiffAnalysis], None]
    status_callback: Optional[Callable[[str], None]] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[DiffAnalysis] = None
    error: Optional[str] = None

class AnalysisQueue:
    """Manages asynchronous LLM analysis tasks"""
    
    def __init__(self, llm_analyzer: LLMAnalyzer):
        self.llm = llm_analyzer
        self.task_queue = queue.Queue()
        self.tasks = {}  # task_id -> AnalysisTask
        self.worker_thread = None
        self.running = False
        
    def start(self):
        """Start the background worker thread"""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    
    def stop(self):
        """Stop the background worker"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1)
    
    def add_task(self, task: AnalysisTask) -> str:
        """Add analysis task to queue"""
        self.tasks[task.id] = task
        self.task_queue.put(task.id)
        return task.id
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a specific task"""
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.FAILED
            task.error = "Cancelled by user"
            return True
        return False
    
    def get_queue_size(self) -> int:
        """Get number of pending tasks"""
        return self.task_queue.qsize()
    
    def get_active_tasks(self) -> list:
        """Get list of all active tasks"""
        return [
            {
                "id": task.id,
                "context": task.context,
                "level": task.level.value,
                "status": task.status.value
            }
            for task in self.tasks.values()
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        ]
    
    def get_commit_analysis_status(self, commit_hash: str, short_hash: str = None, prev_short_hash: str = None) -> dict:
        """Get analysis status for a specific commit"""
        status = {"brief": None, "deep": None}
        
        for task in self.tasks.values():
            # Check for exact pattern: prev_hash→current_hash
            if prev_short_hash and short_hash:
                pattern = f"{prev_short_hash}→{short_hash}"
                if pattern in task.context:
                    level = task.level.value
                    if level == "brief":
                        status["brief"] = task.status.value
                    elif level == "detailed":  # AnalysisLevel.DETAILED has value "detailed" not "deep"
                        status["deep"] = task.status.value
            # Fallback to broader search if pattern not provided
            elif (commit_hash in task.context or 
                  (short_hash and short_hash in task.context)):
                level = task.level.value
                if level == "brief":
                    status["brief"] = task.status.value
                elif level == "detailed":  # AnalysisLevel.DETAILED has value "detailed" not "deep"
                    status["deep"] = task.status.value
        
        return status
    
    def _worker(self):
        """Background worker that processes analysis tasks"""
        while self.running:
            try:
                # Get next task (with timeout to allow clean shutdown)
                try:
                    task_id = self.task_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                task = self.tasks.get(task_id)
                if not task or task.status != TaskStatus.PENDING:
                    continue
                
                # Update status
                task.status = TaskStatus.RUNNING
                # Don't send starting status to avoid cluttering navigation bar
                # if task.status_callback:
                #     task.status_callback(f"🚀 Starting analysis: {task.context}")
                
                try:
                    # Run the analysis
                    result = self.llm.analyze_diff(
                        task.old_text,
                        task.new_text, 
                        task.context,
                        task.level,
                        task.status_callback
                    )
                    
                    # Mark as completed
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    
                    # Notify completion
                    if task.callback:
                        try:
                            task.callback(result)
                        except Exception as cb_error:
                            print(f"Callback error: {cb_error}")
                            if task.status_callback:
                                task.status_callback(f"⚠️ Callback failed: {str(cb_error)[:30]}")
                        
                except Exception as e:
                    # Mark as failed
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    
                    if task.status_callback:
                        task.status_callback(f"❌ Analysis failed: {str(e)[:50]}")
                
            except Exception as e:
                # Log error but keep worker running
                print(f"Worker error: {e}")
                continue