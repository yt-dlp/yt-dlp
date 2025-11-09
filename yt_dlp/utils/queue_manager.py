import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..compat import compat_expanduser
from ._utils import expand_path


class QueueItem:
    """Represents a single item in the download queue"""
    
    def __init__(self, url: str, options: Dict[str, Any] = None, priority: str = 'normal'):
        self.id = str(uuid.uuid4())
        self.url = url
        self.options = options or {}
        self.priority = priority
        self.status = 'pending'  # pending, downloading, completed, failed, paused
        self.added_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.retry_count = 0
        self.max_retries = 3
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'url': self.url,
            'options': self.options,
            'priority': self.priority,
            'status': self.status,
            'added_at': self.added_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create from dictionary (for JSON deserialization)"""
        item = cls(data['url'], data.get('options', {}), data.get('priority', 'normal'))
        item.id = data['id']
        item.status = data.get('status', 'pending')
        item.added_at = data.get('added_at', datetime.now().isoformat())
        item.started_at = data.get('started_at')
        item.completed_at = data.get('completed_at')
        item.error_message = data.get('error_message')
        item.retry_count = data.get('retry_count', 0)
        item.max_retries = data.get('max_retries', 3)
        return item


class PersistentQueue:
    """Manages persistent download queue with file storage"""
    
    def __init__(self, queue_file: Optional[str] = None):
        """
        Initialize persistent queue
        
        @param queue_file: Path to queue file. If None, uses default ~/.yt-dlp-queue.json
        """
        if queue_file is None:
            # Use home directory: ~/.yt-dlp-queue.json
            queue_file = os.path.join(compat_expanduser('~'), '.yt-dlp-queue.json')
        else:
            # Expand user directory and variables in custom path
            queue_file = expand_path(queue_file)
        
        self.queue_file = queue_file
        self.items: Dict[str, QueueItem] = {}
        self._load_queue()
    
    def _load_queue(self):
        """Load queue from file"""
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.items = {
                        item_id: QueueItem.from_dict(item_data)
                        for item_id, item_data in data.get('items', {}).items()
                    }
            except (json.JSONDecodeError, KeyError, IOError) as e:
                # If file is corrupted, create backup and start fresh
                backup_file = f'{self.queue_file}.backup.{int(time.time())}'
                try:
                    os.rename(self.queue_file, backup_file)
                except OSError:
                    pass
                self.items = {}
        else:
            self.items = {}
    
    def _save_queue(self):
        """Save queue to file"""
        try:
            # Ensure directory exists
            queue_dir = os.path.dirname(self.queue_file)
            if queue_dir and not os.path.exists(queue_dir):
                os.makedirs(queue_dir, exist_ok=True)
            
            # Save to temporary file first, then rename (atomic write)
            temp_file = f'{self.queue_file}.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'version': '1.0',
                    'last_updated': datetime.now().isoformat(),
                    'items': {item_id: item.to_dict() for item_id, item in self.items.items()}
                }, f, indent=2)
            
            # Atomic rename
            if os.path.exists(self.queue_file):
                os.replace(temp_file, self.queue_file)
            else:
                os.rename(temp_file, self.queue_file)
        except (IOError, OSError) as e:
            # If save fails, items remain in memory
            raise IOError(f'Failed to save queue file: {e}')
    
    def add_item(self, url: str, options: Dict[str, Any] = None, priority: str = 'normal') -> Optional[str]:
        """Add new item to queue. Returns item ID if added, None if duplicate."""
        # Check for duplicate URL (pending or downloading)
        if self.has_duplicate_url(url):
            return None
        
        item = QueueItem(url, options, priority)
        self.items[item.id] = item
        self._save_queue()
        return item.id
    
    def remove_item(self, item_id: str) -> bool:
        """Remove item from queue"""
        if item_id in self.items:
            del self.items[item_id]
            self._save_queue()
            return True
        return False
    
    def get_item(self, item_id: str) -> Optional[QueueItem]:
        """Get item by ID"""
        return self.items.get(item_id)
    
    def find_item_by_url(self, url: str, status_filter: Optional[List[str]] = None) -> Optional[QueueItem]:
        """Find item by URL, optionally filtered by status"""
        for item in self.items.values():
            if item.url == url:
                if status_filter is None or item.status in status_filter:
                    return item
        return None
    
    def has_duplicate_url(self, url: str) -> bool:
        """Check if URL already exists in queue (pending or downloading)"""
        # Check for duplicates in pending or downloading status
        # Allow re-adding completed or failed items
        return self.find_item_by_url(url, ['pending', 'downloading']) is not None
    
    def get_pending_items(self, priority: Optional[str] = None) -> List[QueueItem]:
        """Get pending items, optionally filtered by priority"""
        items = [item for item in self.items.values() if item.status == 'pending']
        if priority:
            items = [item for item in items if item.priority == priority]
        
        # Sort by priority then by added_at
        priority_order = {'high': 0, 'normal': 1, 'low': 2}
        return sorted(items, key=lambda x: (
            priority_order.get(x.priority, 1),
            x.added_at
        ))
    
    def get_failed_items(self) -> List[QueueItem]:
        """Get all failed items"""
        return [item for item in self.items.values() if item.status == 'failed']
    
    def retry_item(self, item_id: str) -> bool:
        """Reset failed item back to pending for retry"""
        if item_id in self.items:
            item = self.items[item_id]
            if item.status == 'failed':
                item.status = 'pending'
                item.error_message = None
                item.started_at = None
                item.completed_at = None
                # Keep retry_count for tracking
                self._save_queue()
                return True
        return False
    
    def retry_all_failed(self) -> int:
        """Reset all failed items back to pending"""
        count = 0
        for item in self.items.values():
            if item.status == 'failed':
                item.status = 'pending'
                item.error_message = None
                item.started_at = None
                item.completed_at = None
                count += 1
        if count > 0:
            self._save_queue()
        return count
    
    def update_item_status(self, item_id: str, status: str, **kwargs):
        """Update item status and other properties"""
        if item_id in self.items:
            item = self.items[item_id]
            item.status = status
            for key, value in kwargs.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            self._save_queue()
    
    def clear_queue(self, status: Optional[str] = None):
        """Clear queue, optionally filtered by status"""
        if status:
            self.items = {k: v for k, v in self.items.items() if v.status != status}
        else:
            self.items = {}
        self._save_queue()
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = {
            'total': len(self.items),
            'pending': 0,
            'downloading': 0,
            'completed': 0,
            'failed': 0,
            'paused': 0
        }
        
        for item in self.items.values():
            stats[item.status] = stats.get(item.status, 0) + 1
        
        return stats
    
    def get_queue_summary(self) -> str:
        """Get human-readable queue summary"""
        stats = self.get_queue_stats()
        return (
            f"Queue Status: {stats['total']} total items\n"
            f"  Pending: {stats['pending']}\n"
            f"  Downloading: {stats['downloading']}\n"
            f"  Completed: {stats['completed']}\n"
            f"  Failed: {stats['failed']}\n"
            f"  Paused: {stats['paused']}"
        )
