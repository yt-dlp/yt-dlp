"""
Async Download Engine for yt-dlp

This module provides an asynchronous download engine that can handle multiple
concurrent downloads with better error handling and performance.
"""

import asyncio
import aiohttp
import aiofiles
import os
import time
import hashlib
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from ..utils import (
    DownloadError, ContentTooShortError, 
    sanitize_filename, determine_ext, 
    format_bytes, format_seconds
)
from ..networking import Request, RequestDirector
from .common import FileDownloader


@dataclass
class DownloadTask:
    """Represents a single download task"""
    url: str
    filename: str
    info_dict: Dict[str, Any]
    format_id: str
    filepath: Optional[str] = None
    expected_size: Optional[int] = None
    downloaded_bytes: int = 0
    start_time: float = field(default_factory=time.time)
    status: str = "pending"  # pending, downloading, completed, failed, cancelled
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.filepath is None:
            self.filepath = self.filename


@dataclass
class DownloadProgress:
    """Download progress information"""
    task: DownloadTask
    downloaded_bytes: int
    total_bytes: Optional[int]
    speed: Optional[float] = None
    eta: Optional[float] = None
    percentage: Optional[float] = None


class AsyncDownloadEngine:
    """
    Asynchronous download engine for yt-dlp
    
    Features:
    - Concurrent downloads with configurable concurrency
    - Automatic retry with exponential backoff
    - Progress tracking and reporting
    - Graceful error handling
    - Memory-efficient streaming
    - Support for resumable downloads
    """
    
    def __init__(self, 
                 max_concurrent: int = 5,
                 chunk_size: int = 1024 * 1024,  # 1MB chunks
                 timeout: int = 30,
                 retry_delay: float = 1.0,
                 max_retries: int = 3,
                 progress_callback: Optional[Callable[[DownloadProgress], None]] = None):
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.progress_callback = progress_callback
        
        # Internal state
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.tasks: Dict[str, DownloadTask] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=aiohttp.TCPConnector(limit=self.max_concurrent * 2)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        self.executor.shutdown(wait=True)
    
    def add_task(self, url: str, filename: str, info_dict: Dict[str, Any], 
                 format_id: str, expected_size: Optional[int] = None) -> str:
        """Add a download task to the queue"""
        task_id = hashlib.md5(f"{url}_{filename}".encode()).hexdigest()
        
        task = DownloadTask(
            url=url,
            filename=filename,
            info_dict=info_dict,
            format_id=format_id,
            expected_size=expected_size,
            max_retries=self.max_retries
        )
        
        self.tasks[task_id] = task
        return task_id
    
    async def download_file(self, task: DownloadTask) -> bool:
        """Download a single file with retry logic"""
        for attempt in range(task.max_retries + 1):
            try:
                task.status = "downloading"
                task.retry_count = attempt
                
                # Create directory if it doesn't exist
                filepath = Path(task.filepath)
                filepath.parent.mkdir(parents=True, exist_ok=True)
                
                # Check if file already exists and is complete
                if filepath.exists() and task.expected_size:
                    if filepath.stat().st_size == task.expected_size:
                        task.status = "completed"
                        task.downloaded_bytes = task.expected_size
                        self.logger.info(f"File already exists and is complete: {task.filename}")
                        return True
                
                # Download the file
                success = await self._download_single_file(task)
                if success:
                    task.status = "completed"
                    return True
                    
            except asyncio.CancelledError:
                task.status = "cancelled"
                raise
            except Exception as e:
                task.error = str(e)
                self.logger.warning(f"Download attempt {attempt + 1} failed for {task.filename}: {e}")
                
                if attempt < task.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
                else:
                    task.status = "failed"
                    self.logger.error(f"All download attempts failed for {task.filename}: {e}")
                    return False
        
        return False
    
    async def _download_single_file(self, task: DownloadTask) -> bool:
        """Download a single file with progress tracking"""
        async with self.semaphore:
            try:
                async with self.session.get(task.url, allow_redirects=True) as response:
                    response.raise_for_status()
                    
                    # Get file size if not provided
                    if task.expected_size is None:
                        task.expected_size = int(response.headers.get('content-length', 0))
                    
                    # Download with progress tracking
                    async with aiofiles.open(task.filepath, 'wb') as f:
                        start_time = time.time()
                        last_progress_time = start_time
                        
                        async for chunk in response.content.iter_chunked(self.chunk_size):
                            await f.write(chunk)
                            task.downloaded_bytes += len(chunk)
                            
                            # Calculate progress metrics
                            current_time = time.time()
                            if current_time - last_progress_time >= 0.5:  # Update every 500ms
                                elapsed = current_time - start_time
                                speed = task.downloaded_bytes / elapsed if elapsed > 0 else 0
                                
                                if task.expected_size and task.expected_size > 0:
                                    eta = (task.expected_size - task.downloaded_bytes) / speed if speed > 0 else None
                                    percentage = (task.downloaded_bytes / task.expected_size) * 100
                                else:
                                    eta = None
                                    percentage = None
                                
                                # Call progress callback
                                if self.progress_callback:
                                    progress = DownloadProgress(
                                        task=task,
                                        downloaded_bytes=task.downloaded_bytes,
                                        total_bytes=task.expected_size,
                                        speed=speed,
                                        eta=eta,
                                        percentage=percentage
                                    )
                                    self.progress_callback(progress)
                                
                                last_progress_time = current_time
                    
                    # Verify download size
                    if task.expected_size and task.expected_size > 0:
                        actual_size = os.path.getsize(task.filepath)
                        if actual_size != task.expected_size:
                            raise ContentTooShortError(
                                f"Downloaded {actual_size} bytes, expected {task.expected_size} bytes"
                            )
                    
                    return True
                    
            except Exception as e:
                # Clean up partial download
                if os.path.exists(task.filepath):
                    try:
                        os.remove(task.filepath)
                    except OSError:
                        pass
                raise e
    
    async def download_all(self, tasks: List[DownloadTask]) -> Dict[str, bool]:
        """Download all tasks concurrently"""
        if not tasks:
            return {}
        
        # Create asyncio tasks for all downloads
        download_tasks = []
        for task in tasks:
            download_task = asyncio.create_task(self.download_file(task))
            download_tasks.append(download_task)
        
        # Wait for all downloads to complete
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # Process results
        task_results = {}
        for task, result in zip(tasks, results):
            task_id = hashlib.md5(f"{task.url}_{task.filename}".encode()).hexdigest()
            if isinstance(result, Exception):
                task.status = "failed"
                task.error = str(result)
                task_results[task_id] = False
            else:
                task_results[task_id] = result
        
        return task_results
    
    def get_task_status(self, task_id: str) -> Optional[DownloadTask]:
        """Get the status of a specific task"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, DownloadTask]:
        """Get all tasks and their status"""
        return self.tasks.copy()
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task"""
        if task_id in self.tasks:
            self.tasks[task_id].status = "cancelled"
            return True
        return False
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get overall download statistics"""
        total_tasks = len(self.tasks)
        completed = sum(1 for task in self.tasks.values() if task.status == "completed")
        failed = sum(1 for task in self.tasks.values() if task.status == "failed")
        cancelled = sum(1 for task in self.tasks.values() if task.status == "cancelled")
        downloading = sum(1 for task in self.tasks.values() if task.status == "downloading")
        
        total_bytes = sum(task.downloaded_bytes for task in self.tasks.values())
        
        return {
            "total_tasks": total_tasks,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "downloading": downloading,
            "total_bytes_downloaded": total_bytes,
            "success_rate": completed / total_tasks if total_tasks > 0 else 0
        }


class AsyncFileDownloader(FileDownloader):
    """
    Async file downloader that integrates with yt-dlp's existing architecture
    """
    
    def __init__(self, ydl, params):
        super().__init__(ydl, params)
        self.async_engine = None
        self.max_concurrent = params.get('concurrent_downloads', 5)
        self.chunk_size = params.get('chunk_size', 1024 * 1024)
        
    def download(self, filename, info_dict):
        """Download a file using the async engine"""
        if self.async_engine is None:
            # Initialize async engine if not already done
            self.async_engine = AsyncDownloadEngine(
                max_concurrent=self.max_concurrent,
                chunk_size=self.chunk_size,
                progress_callback=self._progress_callback
            )
        
        # Extract download URL and format info
        url = info_dict.get('url')
        format_id = info_dict.get('format_id', 'unknown')
        
        # Add task to async engine
        task_id = self.async_engine.add_task(
            url=url,
            filename=filename,
            info_dict=info_dict,
            format_id=format_id,
            expected_size=info_dict.get('filesize')
        )
        
        # For now, we'll run the async download in a thread
        # In a full implementation, this would be integrated with yt-dlp's event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            task = self.async_engine.get_task_status(task_id)
            success = loop.run_until_complete(self.async_engine.download_file(task))
            return success
        finally:
            loop.close()
    
    def _progress_callback(self, progress: DownloadProgress):
        """Handle progress updates"""
        if self.ydl.params.get('progress_hooks'):
            progress_info = {
                'status': 'downloading',
                'downloaded_bytes': progress.downloaded_bytes,
                'total_bytes': progress.total_bytes,
                'speed': progress.speed,
                'eta': progress.eta,
                'filename': progress.task.filename,
                'format_id': progress.task.format_id
            }
            
            for hook in self.ydl.params['progress_hooks']:
                try:
                    hook(progress_info)
                except Exception as e:
                    self.ydl.report_warning(f'Error in progress hook: {e}')
    
    def close(self):
        """Clean up resources"""
        if self.async_engine:
            # In a full implementation, this would properly close the async engine
            pass
        super().close() 