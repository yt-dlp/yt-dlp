# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    get_element_by_class,
    get_element_by_id,
    parse_duration,
    str_to_int,
    unified_timestamp,
    urlencode_postdata,
)


class TwitCastingIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?twitcasting\.tv/(?P<uploader_id>[^/]+)/movie/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://twitcasting.tv/ivetesangalo/movie/2357609',
        'md5': '745243cad58c4681dc752490f7540d7f',
        'info_dict': {
            'id': '2357609',
            'ext': 'mp4',
            'title': 'Live #2357609',
            'uploader_id': 'ivetesangalo',
            'description': 'Twitter Oficial da cantora brasileira Ivete Sangalo.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20110822',
            'timestamp': 1314010824,
            'duration': 32,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://twitcasting.tv/mttbernardini/movie/3689740',
        'info_dict': {
            'id': '3689740',
            'ext': 'mp4',
            'title': 'Live playing something #3689740',
            'uploader_id': 'mttbernardini',
            'description': 'Salve, io sono Matto (ma con la e). Questa è la mia presentazione, in quanto sono letteralmente matto (nel senso di strano), con qualcosa in più.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20120212',
            'timestamp': 1329028024,
            'duration': 681,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
            'videopassword': 'abc',
        },
    }]

    def _real_extract(self, url):
        uploader_id, video_id = re.match(self._VALID_URL, url).groups()

        video_password = self._downloader.params.get('videopassword')
        request_data = None
        if video_password:
            request_data = urlencode_postdata({
                'password': video_password,
            })
        webpage = self._download_webpage(url, video_id, data=request_data)

        title = clean_html(get_element_by_id(
            'movietitle', webpage)) or self._html_search_meta(
            ['og:title', 'twitter:title'], webpage, fatal=True)

        video_js_data = {}
        m3u8_url = self._search_regex(
            r'data-movie-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
            webpage, 'm3u8 url', group='url', default=None)
        if not m3u8_url:
            video_js_data = self._parse_json(self._search_regex(
                r"data-movie-playlist='(\[[^']+\])'",
                webpage, 'movie playlist'), video_id)[0]
            m3u8_url = video_js_data['source']['url']

        # use `m3u8` entry_protocol until EXT-X-MAP is properly supported by `m3u8_native` entry_protocol
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4', m3u8_id='hls')

        thumbnail = video_js_data.get('thumbnailUrl') or self._og_search_thumbnail(webpage)
        description = clean_html(get_element_by_id(
            'authorcomment', webpage)) or self._html_search_meta(
            ['description', 'og:description', 'twitter:description'], webpage)
        duration = float_or_none(video_js_data.get(
            'duration'), 1000) or parse_duration(clean_html(
                get_element_by_class('tw-player-duration-time', webpage)))
        view_count = str_to_int(self._search_regex(
            r'Total\s*:\s*([\d,]+)\s*Views', webpage, 'views', None))
        timestamp = unified_timestamp(self._search_regex(
            r'data-toggle="true"[^>]+datetime="([^"]+)"',
            webpage, 'datetime', None))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
        }
