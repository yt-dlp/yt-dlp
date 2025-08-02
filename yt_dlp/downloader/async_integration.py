"""
Async Download Integration for yt-dlp

This module provides integration between the async download engine and yt-dlp's
existing architecture, allowing for gradual migration to async downloads.
"""

import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import time
import logging
import hashlib

from .async_downloader import AsyncDownloadEngine, DownloadTask, DownloadProgress
from .common import FileDownloader
from ..utils import DownloadError


@dataclass
class AsyncDownloadConfig:
    """Configuration for async downloads"""
    enabled: bool = True
    max_concurrent: int = 5
    chunk_size: int = 1024 * 1024  # 1MB
    timeout: int = 30
    retry_delay: float = 1.0
    max_retries: int = 3
    progress_update_interval: float = 0.5  # seconds


class AsyncDownloadManager:
    """
    Manages async downloads and provides integration with yt-dlp's existing system
    """
    
    def __init__(self, ydl, config: AsyncDownloadConfig):
        self.ydl = ydl
        self.config = config
        self.engine: Optional[AsyncDownloadEngine] = None
        self.download_queue: List[DownloadTask] = []
        self.active_downloads: Dict[str, DownloadTask] = {}
        self.completed_downloads: Dict[str, DownloadTask] = {}
        self.failed_downloads: Dict[str, DownloadTask] = {}
        
        # Threading
        self._lock = threading.Lock()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._download_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the async download manager"""
        if not self.config.enabled:
            return
            
        with self._lock:
            if self._running:
                return
                
            self._running = True
            self._download_thread = threading.Thread(target=self._run_download_loop, daemon=True)
            self._download_thread.start()
            self.logger.info("Async download manager started")
    
    def stop(self):
        """Stop the async download manager"""
        with self._lock:
            if not self._running:
                return
                
            self._running = False
            
        if self._download_thread:
            self._download_thread.join(timeout=5)
            
        if self.engine:
            # Clean up engine
            pass
            
        self.logger.info("Async download manager stopped")
    
    def _run_download_loop(self):
        """Run the async download loop in a separate thread"""
        try:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            
            self._event_loop.run_until_complete(self._download_worker())
        except Exception as e:
            self.logger.error(f"Error in download loop: {e}")
        finally:
            if self._event_loop:
                self._event_loop.close()
    
    async def _download_worker(self):
        """Main download worker that processes the download queue"""
        async with AsyncDownloadEngine(
            max_concurrent=self.config.max_concurrent,
            chunk_size=self.config.chunk_size,
            timeout=self.config.timeout,
            retry_delay=self.config.retry_delay,
            max_retries=self.config.max_retries,
            progress_callback=self._progress_callback
        ) as engine:
            self.engine = engine
            
            while self._running:
                # Get pending downloads
                with self._lock:
                    pending = self.download_queue.copy()
                    self.download_queue.clear()
                
                if pending:
                    # Add tasks to engine
                    for task in pending:
                        task_id = engine.add_task(
                            url=task.url,
                            filename=task.filename,
                            info_dict=task.info_dict,
                            format_id=task.format_id,
                            expected_size=task.expected_size
                        )
                        self.active_downloads[task_id] = task
                    
                    # Download all pending tasks
                    results = await engine.download_all(pending)
                    
                    # Process results
                    for task_id, success in results.items():
                        task = self.active_downloads.pop(task_id, None)
                        if task:
                            if success:
                                self.completed_downloads[task_id] = task
                            else:
                                self.failed_downloads[task_id] = task
                
                # Sleep before next iteration
                await asyncio.sleep(0.1)
    
    def _progress_callback(self, progress: DownloadProgress):
        """Handle progress updates from the async engine"""
        # Convert to yt-dlp progress format
        progress_info = {
            'status': 'downloading',
            'downloaded_bytes': progress.downloaded_bytes,
            'total_bytes': progress.total_bytes,
            'speed': progress.speed,
            'eta': progress.eta,
            'filename': progress.task.filename,
            'format_id': progress.task.format_id
        }
        
        # Call yt-dlp progress hooks
        if self.ydl.params.get('progress_hooks'):
            for hook in self.ydl.params['progress_hooks']:
                try:
                    hook(progress_info)
                except Exception as e:
                    self.ydl.report_warning(f'Error in progress hook: {e}')
    
    def add_download(self, url: str, filename: str, info_dict: Dict[str, Any], 
                    format_id: str, expected_size: Optional[int] = None) -> str:
        """Add a download to the queue"""
        task = DownloadTask(
            url=url,
            filename=filename,
            info_dict=info_dict,
            format_id=format_id,
            expected_size=expected_size,
            max_retries=self.config.max_retries
        )
        
        with self._lock:
            self.download_queue.append(task)
        
        return hashlib.md5(f"{url}_{filename}".encode()).hexdigest()
    
    def get_download_status(self, task_id: str) -> Optional[DownloadTask]:
        """Get the status of a specific download"""
        with self._lock:
            return (self.active_downloads.get(task_id) or 
                   self.completed_downloads.get(task_id) or 
                   self.failed_downloads.get(task_id))
    
    def cancel_download(self, task_id: str) -> bool:
        """Cancel a specific download"""
        with self._lock:
            if task_id in self.active_downloads:
                task = self.active_downloads.pop(task_id)
                task.status = "cancelled"
                return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get download statistics"""
        with self._lock:
            total_active = len(self.active_downloads)
            total_completed = len(self.completed_downloads)
            total_failed = len(self.failed_downloads)
            total_queued = len(self.download_queue)
            
            return {
                "active_downloads": total_active,
                "completed_downloads": total_completed,
                "failed_downloads": total_failed,
                "queued_downloads": total_queued,
                "total_downloads": total_active + total_completed + total_failed + total_queued
            }


class AsyncFileDownloader(FileDownloader):
    """
    Enhanced file downloader that uses async downloads when enabled
    """
    
    def __init__(self, ydl, params):
        super().__init__(ydl, params)
        
        # Initialize async configuration
        self.async_config = AsyncDownloadConfig(
            enabled=params.get('async_downloads', True),
            max_concurrent=params.get('concurrent_downloads', 5),
            chunk_size=params.get('chunk_size', 1024 * 1024),
            timeout=params.get('timeout', 30),
            retry_delay=params.get('retry_delay', 1.0),
            max_retries=params.get('max_retries', 3)
        )
        
        # Initialize async manager
        self.async_manager = AsyncDownloadManager(ydl, self.async_config)
        
        # Start async manager if enabled
        if self.async_config.enabled:
            self.async_manager.start()
    
    def download(self, filename, info_dict):
        """Download a file using async or fallback to sync"""
        if not self.async_config.enabled:
            # Fallback to original downloader
            return super().download(filename, info_dict)
        
        # Extract download information
        url = info_dict.get('url')
        format_id = info_dict.get('format_id', 'unknown')
        expected_size = info_dict.get('filesize')
        
        if not url:
            raise DownloadError("No URL provided for download")
        
        # Add to async download queue
        task_id = self.async_manager.add_download(
            url=url,
            filename=filename,
            info_dict=info_dict,
            format_id=format_id,
            expected_size=expected_size
        )
        
        # Wait for download to complete (with timeout)
        start_time = time.time()
        timeout = self.async_config.timeout * 2  # Double the timeout for safety
        
        while time.time() - start_time < timeout:
            task = self.async_manager.get_download_status(task_id)
            if task:
                if task.status == "completed":
                    return True
                elif task.status == "failed":
                    raise DownloadError(f"Download failed: {task.error}")
                elif task.status == "cancelled":
                    raise DownloadError("Download was cancelled")
            
            time.sleep(0.1)
        
        # Timeout reached
        raise DownloadError("Download timeout")
    
    def close(self):
        """Clean up resources"""
        if self.async_manager:
            self.async_manager.stop()
        super().close()


# Integration with yt-dlp's downloader factory
def get_async_downloader(ydl, params):
    """Factory function to create async downloader"""
    return AsyncFileDownloader(ydl, params)


# Configuration helpers
def configure_async_downloads(params: Dict[str, Any]) -> Dict[str, Any]:
    """Configure async download parameters"""
    # Set default async download parameters
    params.setdefault('async_downloads', True)
    params.setdefault('concurrent_downloads', 5)
    params.setdefault('chunk_size', 1024 * 1024)
    params.setdefault('timeout', 30)
    params.setdefault('retry_delay', 1.0)
    params.setdefault('max_retries', 3)
    
    return params


# Progress reporting utilities
class AsyncProgressReporter:
    """Utility class for reporting async download progress"""
    
    def __init__(self, ydl):
        self.ydl = ydl
        self.start_time = time.time()
        self.last_report_time = self.start_time
    
    def report_progress(self, progress: DownloadProgress):
        """Report download progress in yt-dlp format"""
        current_time = time.time()
        
        # Throttle progress reports
        if current_time - self.last_report_time < 0.5:
            return
        
        self.last_report_time = current_time
        
        # Format progress information
        progress_info = {
            'status': 'downloading',
            'downloaded_bytes': progress.downloaded_bytes,
            'total_bytes': progress.total_bytes,
            'speed': progress.speed,
            'eta': progress.eta,
            'filename': progress.task.filename,
            'format_id': progress.task.format_id,
            'elapsed': current_time - self.start_time
        }
        
        # Call progress hooks
        if self.ydl.params.get('progress_hooks'):
            for hook in self.ydl.params['progress_hooks']:
                try:
                    hook(progress_info)
                except Exception as e:
                    self.ydl.report_warning(f'Error in progress hook: {e}')
        
        # Print progress to screen
        if not self.ydl.params.get('quiet'):
            self._print_progress(progress_info)
    
    def _print_progress(self, progress_info: Dict[str, Any]):
        """Print progress information to screen"""
        filename = progress_info.get('filename', 'Unknown')
        downloaded = progress_info.get('downloaded_bytes', 0)
        total = progress_info.get('total_bytes')
        speed = progress_info.get('speed')
        eta = progress_info.get('eta')
        
        # Format progress string
        progress_str = f"Downloading {filename}"
        
        if total:
            percentage = (downloaded / total) * 100
            progress_str += f" - {percentage:.1f}%"
        
        if speed:
            progress_str += f" - {format_bytes(speed)}/s"
        
        if eta:
            progress_str += f" - ETA: {format_seconds(eta)}"
        
        self.ydl.to_screen(progress_str, skip_eol=True) 