# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unescapeHTML,
    url_or_none,
)


class TVNetIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+)\.tvnet\.gov\.vn/[^/]+/(?:\d+/)?(?P<id>\d+)(?:/|$)'
    _TESTS = [{
        # video
        'url': 'http://de.tvnet.gov.vn/video/109788/vtv1---bac-tuyet-tai-lao-cai-va-ha-giang/tin-nong-24h',
        'md5': 'b4d7abe0252c9b47774760b7519c7558',
        'info_dict': {
            'id': '109788',
            'ext': 'mp4',
            'title': 'VTV1 - Bắc tuyết tại Lào Cai và Hà Giang',
            'thumbnail': r're:(?i)https?://.*\.(?:jpg|png)',
            'is_live': False,
            'view_count': int,
        },
    }, {
        # audio
        'url': 'http://vn.tvnet.gov.vn/radio/27017/vov1---ban-tin-chieu-10062018/doi-song-va-xa-hoi',
        'md5': 'b5875ce9b0a2eecde029216d0e6db2ae',
        'info_dict': {
            'id': '27017',
            'ext': 'm4a',
            'title': 'VOV1 - Bản tin chiều (10/06/2018)',
            'thumbnail': r're:(?i)https?://.*\.(?:jpg|png)',
            'is_live': False,
        },
    }, {
        'url': 'http://us.tvnet.gov.vn/video/118023/129999/ngay-0705',
        'info_dict': {
            'id': '129999',
            'ext': 'mp4',
            'title': 'VTV1 - Quốc hội với cử tri (11/06/2018)',
            'thumbnail': r're:(?i)https?://.*\.(?:jpg|png)',
            'is_live': False,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # live stream
        'url': 'http://us.tvnet.gov.vn/kenh-truyen-hinh/1011/vtv1',
        'info_dict': {
            'id': '1011',
            'ext': 'mp4',
            'title': r're:^VTV1 \| LiveTV [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'thumbnail': r're:(?i)https?://.*\.(?:jpg|png)',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # radio live stream
        'url': 'http://vn.tvnet.gov.vn/kenh-truyen-hinh/1014',
        'info_dict': {
            'id': '1014',
            'ext': 'm4a',
            'title': r're:VOV1 \| LiveTV [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'thumbnail': r're:(?i)https?://.*\.(?:jpg|png)',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://us.tvnet.gov.vn/phim/6136/25510/vtv3---ca-mot-doi-an-oan-tap-1-50/phim-truyen-hinh',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(
            webpage, default=None) or self._html_search_meta(
            'title', webpage, default=None) or self._search_regex(
            r'<title>([^<]+)<', webpage, 'title')
        title = re.sub(r'\s*-\s*TV Net\s*$', '', title)

        if '/video/' in url or '/radio/' in url:
            is_live = False
        elif '/kenh-truyen-hinh/' in url:
            is_live = True
        else:
            is_live = None

        data_file = unescapeHTML(self._search_regex(
            r'data-file=(["\'])(?P<url>(?:https?:)?//.+?)\1', webpage,
            'data file', group='url'))

        stream_urls = set()
        formats = []
        for stream in self._download_json(data_file, video_id):
            if not isinstance(stream, dict):
                continue
            stream_url = url_or_none(stream.get('url'))
            if stream_url in stream_urls or not stream_url:
                continue
            stream_urls.add(stream_url)
            formats.extend(self._extract_m3u8_formats(
                stream_url, video_id, 'mp4',
                entry_protocol='m3u8' if is_live else 'm3u8_native',
                m3u8_id='hls', fatal=False))
        self._sort_formats(formats)

        # better support for radio streams
        if title.startswith('VOV'):
            for f in formats:
                f.update({
                    'ext': 'm4a',
                    'vcodec': 'none',
                })

        thumbnail = self._og_search_thumbnail(
            webpage, default=None) or unescapeHTML(
            self._search_regex(
                r'data-image=(["\'])(?P<url>(?:https?:)?//.+?)\1', webpage,
                'thumbnail', default=None, group='url'))

        view_count = int_or_none(self._search_regex(
            r'(?s)<div[^>]+\bclass=["\'].*?view-count[^>]+>.*?(\d+).*?</div>',
            webpage, 'view count', default=None))

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'is_live': is_live,
            'view_count': view_count,
            'formats': formats,
        }
