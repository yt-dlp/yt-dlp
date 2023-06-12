# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..utils import clean_html, unified_strdate


class Funker530IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?funker530\.com/video/(?P<id>[^/]+)'
    _TEST = {
        'url': 'https://funker530.com/video/azov-patrol-caught-in-open-under-automatic-grenade-launcher-fire/',
        'md5': 'fcb1880a5703f5c17e9191bab27fb822',
        'info_dict': {
            'id': 'v2qbmu4',
            'ext': 'mp4',
            'title': 'Azov Patrol Caught In Open Under Automatic Grenade Launcher Fire',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Funker530',
            'width': 1280,
            'height': 720,
            'fps': 25,
            'duration': 27,
            'upload_date': '20230608',
            'description': 'md5:e717a9120bccae558927dfd0bcbd07a0',
        }
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_id = self._search_regex(
            r'Rumble\("play",\s*\{video:\s*"([^"]+)"',
            webpage, 'video_id')

        metadata_url = f'https://rumble.com/embedJS/{video_id}.{video_id}/?url={url}&args=%5B%22play%22%2C%7B%22video%22%3A%22{video_id}%22%2C%22div%22%3A%22rumblePlayer%22%7D%5D'
        metadata_js = self._download_webpage(metadata_url, video_id, 'Downloading metadata')

        metadata = self.extract_video_metadata(metadata_js, video_id)

        description = self._html_search_regex(
            r'(?s)<div class="row video-desc-paragraph">.*?<p>(.*?)<div style="display: flex; flex-direction: column;',
            webpage, 'description', fatal=False)
        if description:
            description = clean_html(description)

        return {
            'id': video_id,
            'url': metadata['url'],
            'title': metadata['title'],
            'thumbnail': metadata['thumbnail'],
            'uploader': metadata['author'],
            'width': metadata['width'],
            'height': metadata['height'],
            'fps': metadata['fps'],
            'duration': metadata['duration'],
            'upload_date': unified_strdate(metadata['pubDate']),
            'description': description,
            'display_id': display_id,
        }

    @staticmethod
    def clean_json_string(json_string):
        cleaned_json = re.sub(r',\s*\w+:\w+\(\)', '', json_string)
        return cleaned_json

    def extract_video_metadata(self, js_file, video_id):
        video_metadata = {}
        metadata_match = re.search(rf'f\.f\["{video_id}"\]\s*=\s*(\{{.*?\}});', js_file)
        if metadata_match:
            metadata_json = self.clean_json_string(metadata_match.group(1))
            metadata = json.loads(metadata_json)

            # Extract relevant video metadata
            video_metadata["fps"] = metadata.get("fps")
            video_metadata["width"] = metadata.get("w")
            video_metadata["height"] = metadata.get("h")
            video_metadata["url"] = metadata.get("u", {}).get("mp4", {}).get("url")
            video_metadata["thumbnail"] = metadata.get("i")
            video_metadata["title"] = metadata.get("title")
            video_metadata["author"] = metadata.get("author", {}).get("name")
            video_metadata["duration"] = metadata.get("duration")
            video_metadata["pubDate"] = metadata.get("pubDate")

        return video_metadata
