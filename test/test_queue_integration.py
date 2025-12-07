#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import FakeYDL, try_rm
from yt_dlp import YoutubeDL


class TestYoutubeDLQueueIntegration(unittest.TestCase):
    """Test YoutubeDL queue integration"""

    def setUp(self):
        """Set up test environment"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.queue_file = self.temp_file.name

    def tearDown(self):
        """Clean up temporary files"""
        try_rm(self.queue_file)
        import glob
        for backup in glob.glob(f'{self.queue_file}.corrupted.*'):
            try_rm(backup)

    def test_queue_initialization_default(self):
        """Test queue initialization with default file"""
        ydl = FakeYDL({'quiet': True})
        self.assertIsNotNone(ydl.queue)
        self.assertEqual(len(ydl.queue.get_all()), 0)

    def test_queue_initialization_custom_file(self):
        """Test queue initialization with custom file"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        self.assertIsNotNone(ydl.queue)
        self.assertEqual(ydl.queue.queue_file, os.path.abspath(self.queue_file))

    def test_add_to_queue_single_url(self):
        """Test adding single URL to queue"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        ydl.add_to_queue(['https://www.youtube.com/watch?v=test'])
        
        items = ydl.queue.get_all()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, 'https://www.youtube.com/watch?v=test')
        self.assertEqual(items[0].status, 'pending')

    def test_add_to_queue_multiple_urls(self):
        """Test adding multiple URLs to queue"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        urls = [
            'https://www.youtube.com/watch?v=test1',
            'https://www.youtube.com/watch?v=test2',
            'https://www.youtube.com/watch?v=test3'
        ]
        ydl.add_to_queue(urls)
        
        items = ydl.queue.get_all()
        self.assertEqual(len(items), 3)

    def test_add_to_queue_with_options(self):
        """Test adding URLs with options"""
        ydl = FakeYDL({
            'quiet': True,
            'queue_file': self.queue_file,
            'format': 'best[height<=720]',
            'outtmpl': '%(title)s.%(ext)s'
        })
        ydl.add_to_queue(['https://www.youtube.com/watch?v=test'])
        
        items = ydl.queue.get_all()
        self.assertEqual(len(items), 1)
        self.assertIn('format', items[0].options)
        self.assertIn('outtmpl', items[0].options)

    def test_add_to_queue_duplicate(self):
        """Test adding duplicate URL updates existing item"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        url = 'https://www.youtube.com/watch?v=test'
        
        ydl.add_to_queue([url])
        items1 = ydl.queue.get_all()
        self.assertEqual(len(items1), 1)
        
        ydl.add_to_queue([url])
        items2 = ydl.queue.get_all()
        self.assertEqual(len(items2), 1)  # Still only one item
        self.assertEqual(items2[0].id, items1[0].id)  # Same item

    def test_add_to_queue_from_file(self):
        """Test adding URLs from text file"""
        # Create a temporary file with URLs
        temp_url_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_url_file.write('https://www.youtube.com/watch?v=test1\n')
        temp_url_file.write('https://www.youtube.com/watch?v=test2\n')
        temp_url_file.close()
        
        try:
            ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
            ydl.add_to_queue([temp_url_file.name])
            
            items = ydl.queue.get_all()
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0].url, 'https://www.youtube.com/watch?v=test1')
            self.assertEqual(items[1].url, 'https://www.youtube.com/watch?v=test2')
        finally:
            try_rm(temp_url_file.name)

    def test_show_queue_status_empty(self):
        """Test showing queue status when empty"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        ydl.show_queue_status()
        
        # Should not raise exception
        stats = ydl.queue.get_stats()
        self.assertEqual(stats['total'], 0)

    def test_show_queue_status_with_items(self):
        """Test showing queue status with items"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        ydl.add_to_queue(['https://www.youtube.com/watch?v=test1'])
        ydl.queue.update_status(ydl.queue.get_all()[0].id, 'completed')
        ydl.add_to_queue(['https://www.youtube.com/watch?v=test2'])
        
        ydl.show_queue_status()
        stats = ydl.queue.get_stats()
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['pending'], 1)

    def test_remove_queue_item(self):
        """Test removing queue item"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        ydl.add_to_queue(['https://www.youtube.com/watch?v=test'])
        
        items = ydl.queue.get_all()
        item_id = items[0].id
        
        result = ydl.remove_queue_item(item_id)
        self.assertTrue(result)
        self.assertEqual(len(ydl.queue.get_all()), 0)

    def test_remove_queue_item_partial_id(self):
        """Test removing queue item with partial ID"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        ydl.add_to_queue(['https://www.youtube.com/watch?v=test'])
        
        items = ydl.queue.get_all()
        partial_id = items[0].id[:8]
        
        result = ydl.remove_queue_item(partial_id)
        self.assertTrue(result)
        self.assertEqual(len(ydl.queue.get_all()), 0)

    def test_clear_queue(self):
        """Test clearing queue"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        ydl.add_to_queue([
            'https://www.youtube.com/watch?v=test1',
            'https://www.youtube.com/watch?v=test2'
        ])
        
        ydl.clear_queue()
        self.assertEqual(len(ydl.queue.get_all()), 0)

    def test_retry_queue_items_all(self):
        """Test retrying all failed items"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        item_id1 = ydl.queue.add('https://www.youtube.com/watch?v=test1')
        item_id2 = ydl.queue.add('https://www.youtube.com/watch?v=test2')
        
        ydl.queue.update_status(item_id1, 'failed', 'Error 1')
        ydl.queue.update_status(item_id2, 'failed', 'Error 2')
        
        count = ydl.retry_queue_items('all')
        self.assertEqual(count, 2)
        
        items = ydl.queue.get_all('pending')
        self.assertEqual(len(items), 2)

    def test_retry_queue_items_specific(self):
        """Test retrying specific failed item"""
        ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
        item_id = ydl.queue.add('https://www.youtube.com/watch?v=test')
        ydl.queue.update_status(item_id, 'failed', 'Test error')
        
        count = ydl.retry_queue_items(item_id)
        self.assertEqual(count, 1)
        
        item = ydl.queue.get(item_id)
        self.assertEqual(item.status, 'pending')

    def test_load_queue_from_file(self):
        """Test loading queue from file"""
        temp_url_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_url_file.write('https://www.youtube.com/watch?v=test1\n')
        temp_url_file.write('https://www.youtube.com/watch?v=test2\n')
        temp_url_file.close()
        
        try:
            ydl = FakeYDL({'quiet': True, 'queue_file': self.queue_file})
            count = ydl.load_queue_from_file(temp_url_file.name)
            self.assertEqual(count, 2)
            
            items = ydl.queue.get_all()
            self.assertEqual(len(items), 2)
        finally:
            try_rm(temp_url_file.name)


if __name__ == '__main__':
    unittest.main()

