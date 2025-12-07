#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
import tempfile
import json
import time
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import try_rm
from yt_dlp.utils.queue_manager import PersistentQueue, QueueItem


class TestPersistentQueue(unittest.TestCase):
    """Test PersistentQueue functionality"""

    def setUp(self):
        """Create a temporary queue file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.queue_file = self.temp_file.name
        self.queue = PersistentQueue(self.queue_file)

    def tearDown(self):
        """Clean up temporary files"""
        try_rm(self.queue_file)
        # Clean up any backup files
        import glob
        for backup in glob.glob(f'{self.queue_file}.corrupted.*'):
            try_rm(backup)

    def test_queue_initialization(self):
        """Test queue initialization"""
        self.assertIsNotNone(self.queue)
        self.assertEqual(len(self.queue.get_all()), 0)

    def test_add_single_item(self):
        """Test adding a single item to queue"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        self.assertIsNotNone(item_id)
        items = self.queue.get_all()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, 'https://www.youtube.com/watch?v=test')

    def test_add_multiple_items(self):
        """Test adding multiple items to queue"""
        urls = [
            'https://www.youtube.com/watch?v=test1',
            'https://www.youtube.com/watch?v=test2',
            'https://www.youtube.com/watch?v=test3'
        ]
        for url in urls:
            self.queue.add(url)
        items = self.queue.get_all()
        self.assertEqual(len(items), 3)

    def test_add_with_options(self):
        """Test adding item with options"""
        options = {'format': 'best', 'outtmpl': '%(title)s.%(ext)s'}
        item_id = self.queue.add('https://www.youtube.com/watch?v=test', options=options)
        item = self.queue.get(item_id)
        self.assertIsNotNone(item)
        self.assertEqual(item.options, options)

    def test_add_with_priority(self):
        """Test adding items with different priorities"""
        high_id = self.queue.add('https://example.com/high', priority='high')
        normal_id = self.queue.add('https://example.com/normal', priority='normal')
        low_id = self.queue.add('https://example.com/low', priority='low')
        
        items = self.queue.get_all()
        # Should be sorted by priority (high first)
        self.assertEqual(items[0].priority, 'high')
        self.assertEqual(items[1].priority, 'normal')
        self.assertEqual(items[2].priority, 'low')

    def test_add_duplicate_url_pending(self):
        """Test adding duplicate URL when item is pending"""
        url = 'https://www.youtube.com/watch?v=test'
        id1, was_updated1 = self.queue.add(url, update_existing=True)
        id2, was_updated2 = self.queue.add(url, update_existing=True)
        
        self.assertEqual(id1, id2)  # Same ID
        self.assertFalse(was_updated1)  # First add
        self.assertTrue(was_updated2)  # Second add updates
        items = self.queue.get_all()
        self.assertEqual(len(items), 1)  # Only one item

    def test_add_duplicate_url_completed(self):
        """Test adding duplicate URL when item is completed"""
        url = 'https://www.youtube.com/watch?v=test'
        item_id, _ = self.queue.add(url)
        self.queue.update_status(item_id, 'completed')
        
        # Add same URL again - should update and reset to pending
        new_id, was_updated = self.queue.add(url, update_existing=True)
        self.assertEqual(item_id, new_id)
        self.assertTrue(was_updated)
        item = self.queue.get(item_id)
        self.assertEqual(item.status, 'pending')

    def test_add_duplicate_url_failed(self):
        """Test adding duplicate URL when item is failed"""
        url = 'https://www.youtube.com/watch?v=test'
        item_id, _ = self.queue.add(url)
        self.queue.update_status(item_id, 'failed', 'Test error')
        
        # Add same URL again - should update and reset to pending
        new_id, was_updated = self.queue.add(url, update_existing=True)
        self.assertEqual(item_id, new_id)
        self.assertTrue(was_updated)
        item = self.queue.get(item_id)
        self.assertEqual(item.status, 'pending')
        self.assertIsNone(item.error_message)

    def test_remove_item(self):
        """Test removing item from queue"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        self.assertTrue(self.queue.remove(item_id))
        items = self.queue.get_all()
        self.assertEqual(len(items), 0)

    def test_remove_nonexistent_item(self):
        """Test removing non-existent item"""
        self.assertFalse(self.queue.remove('nonexistent-id'))

    def test_remove_partial_id(self):
        """Test removing item with partial ID (first 8 characters)"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        partial_id = item_id[:8]
        self.assertTrue(self.queue.remove(partial_id))
        items = self.queue.get_all()
        self.assertEqual(len(items), 0)

    def test_get_item(self):
        """Test getting item by ID"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        item = self.queue.get(item_id)
        self.assertIsNotNone(item)
        self.assertEqual(item.url, 'https://www.youtube.com/watch?v=test')

    def test_get_nonexistent_item(self):
        """Test getting non-existent item"""
        item = self.queue.get('nonexistent-id')
        self.assertIsNone(item)

    def test_get_partial_id(self):
        """Test getting item with partial ID"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        partial_id = item_id[:8]
        item = self.queue.get(partial_id)
        self.assertIsNotNone(item)
        self.assertEqual(item.id, item_id)

    def test_get_by_url(self):
        """Test getting item by URL"""
        url = 'https://www.youtube.com/watch?v=test'
        item_id = self.queue.add(url)
        item = self.queue.get_by_url(url)
        self.assertIsNotNone(item)
        self.assertEqual(item.id, item_id)

    def test_get_all_pending(self):
        """Test getting all pending items"""
        self.queue.add('https://example.com/1')
        self.queue.add('https://example.com/2')
        item_id = self.queue.add('https://example.com/3')
        self.queue.update_status(item_id, 'completed')
        
        pending = self.queue.get_all('pending')
        self.assertEqual(len(pending), 2)

    def test_get_all_failed(self):
        """Test getting all failed items"""
        item_id1 = self.queue.add('https://example.com/1')
        item_id2 = self.queue.add('https://example.com/2')
        self.queue.update_status(item_id1, 'failed', 'Error 1')
        self.queue.update_status(item_id2, 'failed', 'Error 2')
        
        failed = self.queue.get_all('failed')
        self.assertEqual(len(failed), 2)

    def test_update_status_pending_to_downloading(self):
        """Test updating status from pending to downloading"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        self.queue.update_status(item_id, 'downloading')
        item = self.queue.get(item_id)
        self.assertEqual(item.status, 'downloading')
        self.assertIsNotNone(item.started_at)

    def test_update_status_to_completed(self):
        """Test updating status to completed"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        self.queue.update_status(item_id, 'completed')
        item = self.queue.get(item_id)
        self.assertEqual(item.status, 'completed')
        self.assertIsNotNone(item.completed_at)

    def test_update_status_to_failed(self):
        """Test updating status to failed"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        self.queue.update_status(item_id, 'failed', 'Test error message')
        item = self.queue.get(item_id)
        self.assertEqual(item.status, 'failed')
        self.assertEqual(item.error_message, 'Test error message')
        self.assertEqual(item.retry_count, 1)

    def test_retry_item(self):
        """Test retrying a failed item"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        self.queue.update_status(item_id, 'failed', 'Test error')
        self.assertTrue(self.queue.retry(item_id))
        
        item = self.queue.get(item_id)
        self.assertEqual(item.status, 'pending')
        self.assertIsNone(item.error_message)
        self.assertIsNone(item.started_at)
        self.assertIsNone(item.completed_at)

    def test_retry_partial_id(self):
        """Test retrying with partial ID"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        self.queue.update_status(item_id, 'failed', 'Test error')
        partial_id = item_id[:8]
        self.assertTrue(self.queue.retry(partial_id))
        
        item = self.queue.get(item_id)
        self.assertEqual(item.status, 'pending')

    def test_retry_nonexistent_item(self):
        """Test retrying non-existent item"""
        self.assertFalse(self.queue.retry('nonexistent-id'))

    def test_clear_all(self):
        """Test clearing all items"""
        self.queue.add('https://example.com/1')
        self.queue.add('https://example.com/2')
        self.queue.clear()
        items = self.queue.get_all()
        self.assertEqual(len(items), 0)

    def test_clear_by_status(self):
        """Test clearing items by status"""
        item_id1 = self.queue.add('https://example.com/1')
        item_id2 = self.queue.add('https://example.com/2')
        self.queue.update_status(item_id1, 'completed')
        self.queue.update_status(item_id2, 'failed', 'Error')
        
        self.queue.clear('completed')
        items = self.queue.get_all()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].status, 'failed')

    def test_get_stats(self):
        """Test getting queue statistics"""
        item_id1 = self.queue.add('https://example.com/1')
        item_id2 = self.queue.add('https://example.com/2')
        item_id3 = self.queue.add('https://example.com/3')
        
        self.queue.update_status(item_id1, 'completed')
        self.queue.update_status(item_id2, 'failed', 'Error')
        
        stats = self.queue.get_stats()
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['downloading'], 0)

    def test_persistence(self):
        """Test that queue persists across instances"""
        item_id = self.queue.add('https://www.youtube.com/watch?v=test')
        self.queue._save()
        
        # Create new queue instance with same file
        new_queue = PersistentQueue(self.queue_file)
        items = new_queue.get_all()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, item_id)

    def test_load_from_file(self):
        """Test loading URLs from text file"""
        # Create a temporary file with URLs
        temp_url_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_url_file.write('https://www.youtube.com/watch?v=test1\n')
        temp_url_file.write('https://www.youtube.com/watch?v=test2\n')
        temp_url_file.write('# This is a comment\n')
        temp_url_file.write('https://www.youtube.com/watch?v=test3\n')
        temp_url_file.close()
        
        try:
            count = self.queue.load_from_file(temp_url_file.name)
            self.assertEqual(count, 3)
            items = self.queue.get_all()
            self.assertEqual(len(items), 3)
        finally:
            try_rm(temp_url_file.name)

    def test_load_from_file_with_options(self):
        """Test loading URLs from file with options"""
        temp_url_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_url_file.write('https://www.youtube.com/watch?v=test1\n')
        temp_url_file.close()
        
        try:
            options = {'format': 'best'}
            count = self.queue.load_from_file(temp_url_file.name, options=options)
            self.assertEqual(count, 1)
            items = self.queue.get_all()
            self.assertEqual(items[0].options, options)
        finally:
            try_rm(temp_url_file.name)

    def test_corrupted_file_recovery(self):
        """Test recovery from corrupted queue file"""
        # Write invalid JSON to file
        with open(self.queue_file, 'w') as f:
            f.write('invalid json content')
        
        # Should recover gracefully
        new_queue = PersistentQueue(self.queue_file)
        items = new_queue.get_all()
        self.assertEqual(len(items), 0)  # Should start fresh

    def test_atomic_write(self):
        """Test that queue file writes are atomic"""
        # Add item and save
        self.queue.add('https://www.youtube.com/watch?v=test')
        self.queue._save()
        
        # Verify file exists and is valid JSON
        self.assertTrue(os.path.exists(self.queue_file))
        with open(self.queue_file, 'r') as f:
            data = json.load(f)
            self.assertIn('items', data)
            self.assertEqual(len(data['items']), 1)

    def test_default_queue_file(self):
        """Test default queue file location"""
        with patch('yt_dlp.utils.queue_manager.compat_expanduser', return_value='/home/test'):
            queue = PersistentQueue()
            expected_path = os.path.abspath('/home/test/.yt-dlp-queue.json')
            self.assertEqual(queue.queue_file, expected_path)

    def test_custom_queue_file(self):
        """Test custom queue file location"""
        custom_path = '/custom/path/queue.json'
        queue = PersistentQueue(custom_path)
        self.assertEqual(queue.queue_file, os.path.abspath(custom_path))

    def test_priority_sorting(self):
        """Test that items are sorted by priority"""
        self.queue.add('https://example.com/low1', priority='low')
        self.queue.add('https://example.com/high1', priority='high')
        self.queue.add('https://example.com/normal1', priority='normal')
        self.queue.add('https://example.com/low2', priority='low')
        self.queue.add('https://example.com/high2', priority='high')
        
        items = self.queue.get_all()
        priorities = [item.priority for item in items]
        self.assertEqual(priorities, ['high', 'high', 'normal', 'low', 'low'])

    def test_priority_sorting_with_timestamps(self):
        """Test priority sorting with same priority uses timestamp"""
        time.sleep(0.01)  # Ensure different timestamps
        id1 = self.queue.add('https://example.com/1', priority='normal')
        time.sleep(0.01)
        id2 = self.queue.add('https://example.com/2', priority='normal')
        
        items = self.queue.get_all('pending')
        # Should be sorted by added_at (first added first)
        self.assertEqual(items[0].id, id1)
        self.assertEqual(items[1].id, id2)


if __name__ == '__main__':
    unittest.main()

