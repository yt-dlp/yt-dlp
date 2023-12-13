import re
import json
from .common import InfoExtractor


class NinaProtocolIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ninaprotocol\.com/releases/(?P<id>[a-zA-Z0-9\-]+)'

    _TESTS = [{
        'url': 'https://www.ninaprotocol.com/releases/3xl-nina-label-mix-014',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the audio file (use --test)',
        'info_dict': {
            'id': '3xl-nina-label-mix-014',
            'ext': 'mp3',
            'title': '3XL - Nina Label Mix 014',
            # Add the thumbnail regex extraction here
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # If the title is not within <h1> tags, adjust the regex below.
        title = self._html_search_regex(r'<div class="title">([^<]+)</div>', webpage, 'title', default=None)

        if not title:
            self.report_warning(f'Could not extract title for {video_id}')
            title = video_id  # Use a default title if none is found

        # Extract JSON-like data within JavaScript
        json_str = self._search_regex(
            r'self\.__next_f\.push\(\[1,"24:\[\\"(.+?)\\"\]\]"\)',
            webpage, 'JSON data', fatal=False)

        # Parse JSON data if found
        audio_url = None
        if json_str:
            try:
                # Clean up the JSON string and load it
                json_str = re.sub(r'\\u003c|\\u003e|\\u0026', '', json_str)
                json_data = json.loads(f'[{json_str}]')  # Wrap in array brackets to form valid JSON
                # Navigate through the JSON structure to find the audio URL
                audio_url = json_data[0].get('animation_url')
            except json.JSONDecodeError:
                self.report_warning('Could not parse JSON data for audio URL.')

        # Extract thumbnail
        thumbnail = self._html_search_regex(
            r'<img[^>]+src="([^"]+)"[^>]*alt="[^"]*"', webpage, 'thumbnail', fatal=False)

        return {
            'id': video_id,
            'title': title,
            'url': audio_url,
            'thumbnail': thumbnail,
            # Add additional properties as needed
        }
