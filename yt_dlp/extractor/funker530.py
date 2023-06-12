# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .rumble import RumbleEmbedIE
from ..utils import clean_html


class Funker530IE(InfoExtractor):
    _VALID_URL = r'https?:\/\/(?:www\.)?funker530\.com\/video\/(?P<id>[^\/]+)\/?'
    _TESTS = [{
        'url': 'https://funker530.com/video/azov-patrol-caught-in-open-under-automatic-grenade-launcher-fire/',
        'md5': '085f50fea27523a388bbc22e123e09c8',
        'info_dict': {
            'id': 'v2qbmu4',
            'ext': 'mp4',
            'title': 'Azov Patrol Caught In Open Under Automatic Grenade Launcher Fire',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Funker530',
            'channel': 'Funker530',
            'channel_url': 'https://rumble.com/c/c-1199543',
            'width': 1280,
            'height': 720,
            'fps': 25,
            'duration': 27,
            'upload_date': '20230608',
            'timestamp': 1686241321,
            'live_status': 'not_live',
            'description': 'md5:bea2e1f458095414e04b5ac189c2f980',
        }
    }
        # TODO: add test for embedded YouTube videos
        #     , {
        #     'url': 'https://funker530.com/video/my-friends-joined-the-russians-civdiv/',
        #     'md5': '',
        #     'info_dict': {
        #         'id': '',
        #         'ext': 'mp4',
        #         'title': 'My “Friends” Joined the Russians - CivDiv',
        #         'thumbnail': r're:^https?://.*\.jpg$',
        #         'uploader': '',
        #         'width': ,
        #         'height': ,
        #         'fps': ,
        #         'duration': ,
        #         'upload_date': '',
        #         'description': 'md5:',
        #     }
        # }
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        rumble = RumbleEmbedIE(downloader=self._downloader)
        found_videos = rumble._extract_embed_urls(url, webpage)
        if len(found_videos):
            # TODO: do I need to do all found videos or is [0] ok?
            embedded_video = rumble.extract(found_videos[0])
        else:
            return

        desc_regex = re.compile(r'(?s)<div class="row video-desc-paragraph">.*?<p>(.*?)(About the Author|<\/div>\n?<\/div>\n?<\/div>)')
        # _html_search_regex is not cleaning <style> tags so we'll do it ourselves.
        # description = self._html_search_regex(desc_regex, webpage, 'description', fatal=False)
        description = re.search(desc_regex, webpage).group(1)
        if description:
            description = clean_html(re.sub(r'<style>(.|\s)*?<\/style>', '', description))

        embedded_video['description'] = description
        return embedded_video
