import os.path
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    remove_start,
    url_basename,
)


class DemocracynowIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?democracynow\.org/(?P<id>[^\?]*)'
    IE_NAME = 'democracynow'
    _TESTS = [{
        'url': 'http://www.democracynow.org/shows/2015/7/3',
        'md5': '3757c182d3d84da68f5c8f506c18c196',
        'info_dict': {
            'id': '2015-0703-001',
            'ext': 'mp4',
            'title': 'Daily Show for July 03, 2015',
            'description': 'md5:80eb927244d6749900de6072c7cc2c86',
        },
    }, {
        'url': 'http://www.democracynow.org/2015/7/3/this_flag_comes_down_today_bree',
        'info_dict': {
            'id': '2015-0703-001',
            'ext': 'mp4',
            'title': '"This Flag Comes Down Today": Bree Newsome Scales SC Capitol Flagpole, Takes Down Confederate Flag',
            'description': 'md5:4d2bc4f0d29f5553c2210a4bc7761a21',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        json_data = self._parse_json(self._search_regex(
            r'<script[^>]+type="text/json"[^>]*>\s*({[^>]+})', webpage, 'json'),
            display_id)

        title = json_data['title']
        formats = []

        video_id = None

        for key in ('file', 'audio', 'video', 'high_res_video'):
            media_url = json_data.get(key, '')
            if not media_url:
                continue
            media_url = re.sub(r'\?.*', '', urllib.parse.urljoin(url, media_url))
            video_id = video_id or remove_start(os.path.splitext(url_basename(media_url))[0], 'dn')
            formats.append({
                'url': media_url,
                'vcodec': 'none' if key == 'audio' else None,
            })

        default_lang = 'en'
        subtitles = {}

        def add_subtitle_item(lang, info_dict):
            if lang not in subtitles:
                subtitles[lang] = []
            subtitles[lang].append(info_dict)

        # chapter_file are not subtitles
        if 'caption_file' in json_data:
            add_subtitle_item(default_lang, {
                'url': urllib.parse.urljoin(url, json_data['caption_file']),
            })

        for subtitle_item in json_data.get('captions', []):
            lang = subtitle_item.get('language', '').lower() or default_lang
            add_subtitle_item(lang, {
                'url': urllib.parse.urljoin(url, subtitle_item['url']),
            })

        description = self._og_search_description(webpage, default=None)

        return {
            'id': video_id or display_id,
            'title': title,
            'description': description,
            'thumbnail': json_data.get('image'),
            'subtitles': subtitles,
            'formats': formats,
        }
