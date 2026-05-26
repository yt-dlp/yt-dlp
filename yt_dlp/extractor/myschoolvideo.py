# coding: utf-8
from __future__ import unicode_literals

import re
from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    clean_html,
)


class MySchoolVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?myschoolvideo\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.myschoolvideo.com/video/1024',
        'md5': 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6',
        'info_dict': {
            'id': '1024',
            'ext': 'mp4',
            'title': 'Computer Science Lecture 1',
            'description': 'Introduction to Computer Science and Programming.',
            'uploader': 'Prof. Smith',
            'timestamp': 1716724800,
            'upload_date': '20240526',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        
        # 1. 下载目标视频网页的 HTML 内容
        webpage = self._download_webpage(url, video_id)

        # 2. 从 HTML 的 Meta 标签中提取基础元数据
        title = self._html_search_meta(['og:title', 'title'], webpage, default=None)
        if not title:
            title = self._html_search_regex(r'<h1>(.*?)</h1>', webpage, 'title')

        # 3. 模拟请求该网站的后端 JSON 数据接口
        api_url = 'https://www.myschoolvideo.com/api/v1/video/%s' % video_id
        video_data = self._download_json(api_url, video_id, note='Downloading video JSON metadata')

        # 4. 解析并清洗提取到的音视频流及相关结构化数据
        formats = [{
            'url': item.get('play_url'),
            'format_id': item.get('quality', 'default'),
            'ext': 'mp4',
            'height': int_or_none(item.get('height')),
        } for item in video_data.get('streams', []) if item.get('play_url')]

        # 如果接口未返回流，则尝试从网页中直接提取视频地址
        if not formats:
            fallback_url = self._html_search_regex(r'source\s+src="([^"]+)"', webpage, 'video url')
            formats.append({'url': fallback_url, 'format_id': 'fallback'})

        return {
            'id': video_id,
            'title': title or video_data.get('title'),
            'formats': formats,
            'description': clean_html(video_data.get('description') or self._html_search_meta('description', webpage)),
            'uploader': video_data.get('author', {}).get('name'),
            'timestamp': parse_iso8601(video_data.get('created_at')),
            'view_count': int_or_none(video_data.get('views')),
            'like_count': int_or_none(video_data.get('likes')),
        }