# coding: utf-8
from __future__ import unicode_literals

import datetime

from .common import InfoExtractor
from ..utils import (
    unified_timestamp,
)

class CGTNIE(InfoExtractor):
    _VALID_URL = r'https?://news\.cgtn\.com/news/[0-9]{4}-[0-9]{2}-[0-9]{2}/[a-zA-Z0-9-]+-(?P<id>[a-zA-Z0-9-]+)/index\.html'
    _TESTS = [
        {
            'url': 'https://news.cgtn.com/news/2021-03-09/Up-and-Out-of-Poverty-Ep-1-A-solemn-promise-YuOUaOzGQU/index.html',
            'info_dict': {
                'id': 'YuOUaOzGQU',
                'ext': 'mp4',
                'title': 'Up and Out of Poverty Ep. 1: A solemn promise',
                'thumbnail': r're:^https?://.*\.jpg$',
                'timestamp': 1615295940,
                'upload_date': '20210309',
            }
        },
        {
            'url': 'https://news.cgtn.com/news/2021-06-06/China-Indonesia-vow-to-further-deepen-maritime-cooperation-10REvJCewCY/index.html',
            'info_dict': {
                'id': '10REvJCewCY',
                'ext': 'mp4',
                'title': 'China, Indonesia vow to further deepen maritime cooperation',
                'thumbnail': r're:^https?://.*\.jpg$',
                'description': 'China and Indonesia vowed to upgrade their cooperation into the maritime sector and also for political security, economy, and cultural and people-to-people exchanges.',
                'author': 'CGTN',
                'category': 'China',
                'timestamp': 1622950200,
                'upload_date': '20210606',
            }
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<div class="news-title">(.+?)</div>', webpage, 'title')
        download_url = self._html_search_regex(r'data-video ="(?P<url>.+m3u8)"', webpage, 'download_url')
        thumbnail = self._html_search_regex(r'<div class="cg-player-container J_player_container" .*? data-poster="(?P<thumbnail>.+jpg)" (.*?)>', webpage, 'thumbnail', fatal=False)
        description = self._html_search_meta(('og:description', 'twitter:description', ), webpage, fatal=False)
        category = self._html_search_regex(r'<span class="section">\s*(.+?)\s*</span>', webpage, 'category', fatal=False)
        datetime_str = self._html_search_regex(r'<span class="date">\s*(.+?)\s*</span>', webpage, 'datetime_str', fatal=False)
        author = self._html_search_regex(r'<div class="news-author-name">\s*(.+?)\s*</div>', webpage, 'author', default=None, fatal=False)
        
        timestamp = None
        if datetime_str:
            formatted_datetime_str = datetime.datetime.strptime(datetime_str, '%H:%M, %d-%b-%Y').strftime('%Y/%m/%d %H:%M')
            timestamp = unified_timestamp(formatted_datetime_str) - 8 * 3600

        formats = self._extract_m3u8_formats(
            download_url, video_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'category': category,
            'author': author,
            'timestamp': timestamp
        }
