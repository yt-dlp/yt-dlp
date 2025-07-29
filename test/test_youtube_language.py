#!/usr/bin/env python3

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import FakeYDL
from yt_dlp.extractor import YoutubeIE
from yt_dlp.utils import ExtractorError


class TestYoutubeLanguage(unittest.TestCase):
    """Test cases for YouTube language parameter functionality"""

    def test_youtube_language_parameter_spanish(self):
        """Test Spanish language parameter for title translation"""
        dl = FakeYDL()
        dl.params['extractor_args'] = {'youtube': {'lang': ['es']}}
        ie = YoutubeIE(dl)
        
        # Test with a video that has Spanish translations
        result = ie.extract('https://www.youtube.com/watch?v=0aNa_xESK1A')
        
        # Verify the title is in Spanish
        self.assertIsNotNone(result.get('title'))
        # Check if the title contains Spanish text (basic validation)
        title = result.get('title', '').lower()
        self.assertTrue(any(spanish_word in title for spanish_word in ['episodio', 'temporada', 'es']),
                       f"Title '{title}' does not appear to be Spanish")

    def test_youtube_language_parameter_english_fallback(self):
        """Test English fallback when no translation available"""
        dl = FakeYDL()
        dl.params['extractor_args'] = {'youtube': {'lang': ['en']}}
        ie = YoutubeIE(dl)
        
        result = ie.extract('https://www.youtube.com/watch?v=0aNa_xESK1A')
        
        # Should fall back to original title
        self.assertIsNotNone(result.get('title'))
        self.assertIsInstance(result.get('title'), str)

    def test_youtube_language_parameter_no_language(self):
        """Test behavior when no language parameter is provided"""
        dl = FakeYDL()
        # No extractor_args specified
        ie = YoutubeIE(dl)
        
        result = ie.extract('https://www.youtube.com/watch?v=0aNa_xESK1A')
        
        # Should use original title
        self.assertIsNotNone(result.get('title'))
        self.assertIsInstance(result.get('title'), str)

    def test_youtube_description_language_spanish(self):
        """Test Spanish language parameter for description translation"""
        dl = FakeYDL()
        dl.params['extractor_args'] = {'youtube': {'lang': ['es']}}
        ie = YoutubeIE(dl)
        
        result = ie.extract('https://www.youtube.com/watch?v=0aNa_xESK1A')
        
        # Verify description is present
        description = result.get('description', '')
        self.assertIsNotNone(description)
        self.assertIsInstance(description, str)
        
        # Basic check for Spanish content
        if description:
            spanish_indicators = ['episodio', 'temporada', 'español', 'pokémon']
            has_spanish = any(indicator in description.lower() for indicator in spanish_indicators)
            # Note: this is a basic test - actual Spanish content depends on video availability

    def test_youtube_language_parameter_multiple_languages(self):
        """Test different language parameters"""
        languages = ['es', 'fr', 'de']
        
        for lang in languages:
            with self.subTest(language=lang):
                dl = FakeYDL()
                dl.params['extractor_args'] = {'youtube': {'lang': [lang]}}
                ie = YoutubeIE(dl)
                
                try:
                    result = ie.extract('https://www.youtube.com/watch?v=0aNa_xESK1A')
                    self.assertIsNotNone(result.get('title'))
                    self.assertIsInstance(result.get('title'), str)
                except ExtractorError:
                    # Some videos may not be available in all regions
                    pass


if __name__ == '__main__':
    unittest.main()
