"""Queue management for yt-dlp downloads."""

import json
import os
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from ..compat import compat_expanduser


@dataclass
class QueueItem:
    """Represents a single item in the download queue."""
    id: str
    url: str
    status: str = 'pending'  # pending, downloading, completed, failed
    priority: str = 'normal'  # high, normal, low
    added_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    options: Dict = field(default_factory=dict)  # Download options (format, output, etc.)

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        return cls(**data)


class PersistentQueue:
    """Manages persistent download queue with file storage."""

    QUEUE_VERSION = 1

    def __init__(self, queue_file=None):
        """
        Initialize persistent queue.
        
        Args:
            queue_file: Path to queue file. If None, uses ~/.yt-dlp-queue.json
        """
        if queue_file is None:
            queue_file = os.path.join(compat_expanduser('~'), '.yt-dlp-queue.json')
        self.queue_file = os.path.abspath(os.path.expanduser(queue_file))
        self._items: Dict[str, QueueItem] = {}
        self._load()

    def _load(self):
        """Load queue from file."""
        if not os.path.exists(self.queue_file):
            self._items = {}
            return

        try:
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check version for future compatibility
            version = data.get('version', 1)
            if version != self.QUEUE_VERSION:
                # Handle version migration if needed in future
                pass

            self._items = {}
            for item_data in data.get('items', []):
                try:
                    item = QueueItem.from_dict(item_data)
                    self._items[item.id] = item
                except Exception:
                    # Skip corrupted items
                    continue
        except (json.JSONDecodeError, IOError, OSError) as e:
            # File is corrupted or unreadable, start fresh
            # Try to backup corrupted file
            try:
                backup_file = f'{self.queue_file}.corrupted.{int(time.time())}'
                if os.path.exists(self.queue_file):
                    os.rename(self.queue_file, backup_file)
            except Exception:
                pass
            self._items = {}

    def _save(self):
        """Save queue to file atomically."""
        data = {
            'version': self.QUEUE_VERSION,
            'items': [item.to_dict() for item in self._items.values()]
        }

        # Atomic write: write to temp file, then rename
        try:
            # Create directory if it doesn't exist
            queue_dir = os.path.dirname(self.queue_file)
            if queue_dir and not os.path.exists(queue_dir):
                os.makedirs(queue_dir, exist_ok=True)

            # Write to temporary file in same directory
            fd, temp_path = tempfile.mkstemp(
                dir=queue_dir,
                prefix='.yt-dlp-queue.tmp.',
                suffix='.json',
                text=True
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                # Atomic rename
                os.replace(temp_path, self.queue_file)
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise
        except (IOError, OSError) as e:
            raise RuntimeError(f'Failed to save queue file: {e}') from e

    def add(self, url: str, options: Optional[Dict] = None, priority: str = 'normal') -> str:
        """
        Add URL to queue.
        
        Args:
            url: URL to add
            options: Download options dictionary
            priority: Priority level (high, normal, low)
            
        Returns:
            Item ID
        """
        item_id = str(uuid.uuid4())
        item = QueueItem(
            id=item_id,
            url=url,
            priority=priority,
            options=options or {}
        )
        self._items[item_id] = item
        self._save()
        return item_id

    def remove(self, item_id: str) -> bool:
        """
        Remove item from queue.
        
        Args:
            item_id: Item ID to remove
            
        Returns:
            True if item was removed, False if not found
        """
        if item_id in self._items:
            del self._items[item_id]
            self._save()
            return True
        return False

    def get(self, item_id: str) -> Optional[QueueItem]:
        """Get item by ID."""
        return self._items.get(item_id)

    def get_all(self, status: Optional[str] = None) -> List[QueueItem]:
        """
        Get all items, optionally filtered by status.
        
        Args:
            status: Filter by status (pending, downloading, completed, failed)
            
        Returns:
            List of QueueItem objects
        """
        items = list(self._items.values())
        if status:
            items = [item for item in items if item.status == status]
        # Sort by priority (high first), then by added_at
        priority_order = {'high': 0, 'normal': 1, 'low': 2}
        items.sort(key=lambda x: (priority_order.get(x.priority, 1), x.added_at))
        return items

    def update_status(self, item_id: str, status: str, error_message: Optional[str] = None):
        """
        Update item status.
        
        Args:
            item_id: Item ID
            status: New status
            error_message: Optional error message for failed items
        """
        if item_id not in self._items:
            return
        
        item = self._items[item_id]
        item.status = status
        
        if status == 'downloading' and item.started_at is None:
            item.started_at = time.time()
        elif status in ('completed', 'failed'):
            item.completed_at = time.time()
            if status == 'failed' and error_message:
                item.error_message = error_message
                item.retry_count += 1
        
        self._save()

    def retry(self, item_id: str) -> bool:
        """
        Reset item to pending status for retry.
        
        Args:
            item_id: Item ID to retry
            
        Returns:
            True if item was reset, False if not found
        """
        if item_id not in self._items:
            return False
        
        item = self._items[item_id]
        item.status = 'pending'
        item.started_at = None
        item.completed_at = None
        item.error_message = None
        self._save()
        return True

    def clear(self, status: Optional[str] = None):
        """
        Clear items from queue.
        
        Args:
            status: If specified, only clear items with this status
        """
        if status:
            self._items = {k: v for k, v in self._items.items() if v.status != status}
        else:
            self._items = {}
        self._save()

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        stats = {
            'total': len(self._items),
            'pending': 0,
            'downloading': 0,
            'completed': 0,
            'failed': 0
        }
        for item in self._items.values():
            if item.status in stats:
                stats[item.status] += 1
        return stats

    def load_from_file(self, file_path: str, options: Optional[Dict] = None, priority: str = 'normal') -> int:
        """
        Load URLs from text file into queue.
        
        Args:
            file_path: Path to text file with URLs (one per line)
            options: Download options to apply to all URLs
            priority: Priority level for all URLs
            
        Returns:
            Number of URLs added
        """
        count = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):  # Skip empty lines and comments
                        self.add(url, options, priority)
                        count += 1
            return count
        except (IOError, OSError) as e:
            raise RuntimeError(f'Failed to load URLs from file: {e}') from e

