#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.utils.queue_manager import QueueItem


class TestQueueItem(unittest.TestCase):
    """Test QueueItem dataclass functionality"""

    def test_queue_item_initialization(self):
        """Test basic QueueItem initialization"""
        item = QueueItem(
            id='test-id-123',
            url='https://www.youtube.com/watch?v=test'
        )
        self.assertEqual(item.id, 'test-id-123')
        self.assertEqual(item.url, 'https://www.youtube.com/watch?v=test')
        self.assertEqual(item.status, 'pending')
        self.assertEqual(item.priority, 'normal')
        self.assertIsNotNone(item.added_at)
        self.assertIsNone(item.started_at)
        self.assertIsNone(item.completed_at)
        self.assertIsNone(item.error_message)
        self.assertEqual(item.retry_count, 0)
        self.assertEqual(item.options, {})

    def test_queue_item_with_options(self):
        """Test QueueItem with custom options"""
        options = {'format': 'best', 'outtmpl': '%(title)s.%(ext)s'}
        item = QueueItem(
            id='test-id-456',
            url='https://www.youtube.com/watch?v=test',
            options=options
        )
        self.assertEqual(item.options, options)

    def test_queue_item_with_priority(self):
        """Test QueueItem with different priority levels"""
        for priority in ['high', 'normal', 'low']:
            item = QueueItem(
                id=f'test-id-{priority}',
                url='https://www.youtube.com/watch?v=test',
                priority=priority
            )
            self.assertEqual(item.priority, priority)

    def test_queue_item_unique_id(self):
        """Test that each item has a unique ID"""
        item1 = QueueItem(id='id1', url='https://example.com/1')
        item2 = QueueItem(id='id2', url='https://example.com/2')
        self.assertNotEqual(item1.id, item2.id)

    def test_queue_item_to_dict(self):
        """Test QueueItem serialization to dictionary"""
        item = QueueItem(
            id='test-id',
            url='https://www.youtube.com/watch?v=test',
            status='pending',
            priority='high',
            options={'format': 'best'}
        )
        data = item.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data['id'], 'test-id')
        self.assertEqual(data['url'], 'https://www.youtube.com/watch?v=test')
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['priority'], 'high')
        self.assertEqual(data['options'], {'format': 'best'})
        self.assertIn('added_at', data)

    def test_queue_item_from_dict(self):
        """Test QueueItem deserialization from dictionary"""
        data = {
            'id': 'test-id',
            'url': 'https://www.youtube.com/watch?v=test',
            'status': 'completed',
            'priority': 'low',
            'added_at': time.time(),
            'started_at': time.time(),
            'completed_at': time.time(),
            'error_message': None,
            'retry_count': 1,
            'options': {'format': 'best'}
        }
        item = QueueItem.from_dict(data)
        self.assertEqual(item.id, 'test-id')
        self.assertEqual(item.url, 'https://www.youtube.com/watch?v=test')
        self.assertEqual(item.status, 'completed')
        self.assertEqual(item.priority, 'low')
        self.assertEqual(item.retry_count, 1)
        self.assertEqual(item.options, {'format': 'best'})

    def test_queue_item_roundtrip(self):
        """Test QueueItem serialization roundtrip"""
        original = QueueItem(
            id='test-id',
            url='https://www.youtube.com/watch?v=test',
            status='failed',
            priority='high',
            error_message='Test error',
            retry_count=2,
            options={'format': 'best', 'outtmpl': '%(title)s.%(ext)s'}
        )
        data = original.to_dict()
        restored = QueueItem.from_dict(data)
        self.assertEqual(original.id, restored.id)
        self.assertEqual(original.url, restored.url)
        self.assertEqual(original.status, restored.status)
        self.assertEqual(original.priority, restored.priority)
        self.assertEqual(original.error_message, restored.error_message)
        self.assertEqual(original.retry_count, restored.retry_count)
        self.assertEqual(original.options, restored.options)

    def test_queue_item_empty_options(self):
        """Test QueueItem with empty options"""
        item = QueueItem(id='test-id', url='https://example.com')
        self.assertEqual(item.options, {})
        data = item.to_dict()
        self.assertEqual(data['options'], {})

    def test_queue_item_missing_fields(self):
        """Test QueueItem with missing optional fields in from_dict"""
        data = {
            'id': 'test-id',
            'url': 'https://example.com'
        }
        # Should work with defaults
        item = QueueItem.from_dict(data)
        self.assertEqual(item.id, 'test-id')
        self.assertEqual(item.url, 'https://example.com')
        self.assertEqual(item.status, 'pending')  # default
        self.assertEqual(item.priority, 'normal')  # default


if __name__ == '__main__':
    unittest.main()

