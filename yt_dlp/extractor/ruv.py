# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    unified_timestamp,
)


class RuvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ruv\.is/(?:sarpurinn/[^/]+|node)/(?P<id>[^/]+(?:/\d+)?)'
    _TESTS = [{
        # m3u8
        'url': 'http://ruv.is/sarpurinn/ruv-aukaras/fh-valur/20170516',
        'md5': '66347652f4e13e71936817102acc1724',
        'info_dict': {
            'id': '1144499',
            'display_id': 'fh-valur/20170516',
            'ext': 'mp4',
            'title': 'FH - Valur',
            'description': 'Bein útsending frá 3. leik FH og Vals í úrslitum Olísdeildar karla í handbolta.',
            'timestamp': 1494963600,
            'upload_date': '20170516',
        },
    }, {
        # mp3
        'url': 'http://ruv.is/sarpurinn/ras-2/morgunutvarpid/20170619',
        'md5': '395ea250c8a13e5fdb39d4670ef85378',
        'info_dict': {
            'id': '1153630',
            'display_id': 'morgunutvarpid/20170619',
            'ext': 'mp3',
            'title': 'Morgunútvarpið',
            'description': 'md5:a4cf1202c0a1645ca096b06525915418',
            'timestamp': 1497855000,
            'upload_date': '20170619',
        },
    }, {
        'url': 'http://ruv.is/sarpurinn/ruv/frettir/20170614',
        'only_matching': True,
    }, {
        'url': 'http://www.ruv.is/node/1151854',
        'only_matching': True,
    }, {
        'url': 'http://ruv.is/sarpurinn/klippa/secret-soltice-hefst-a-morgun',
        'only_matching': True,
    }, {
        'url': 'http://ruv.is/sarpurinn/ras-1/morgunvaktin/20170619',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        title = self._og_search_title(webpage)

        FIELD_RE = r'video\.%s\s*=\s*(["\'])(?P<url>(?:(?!\1).)+)\1'

        media_url = self._html_search_regex(
            FIELD_RE % 'src', webpage, 'video URL', group='url')

        video_id = self._search_regex(
            r'<link\b[^>]+\bhref=["\']https?://www\.ruv\.is/node/(\d+)',
            webpage, 'video id', default=display_id)

        ext = determine_ext(media_url)

        if ext == 'm3u8':
            formats = self._extract_m3u8_formats(
                media_url, video_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls')
        elif ext == 'mp3':
            formats = [{
                'format_id': 'mp3',
                'url': media_url,
                'vcodec': 'none',
            }]
        else:
            formats = [{
                'url': media_url,
            }]

        description = self._og_search_description(webpage, default=None)
        thumbnail = self._og_search_thumbnail(
            webpage, default=None) or self._search_regex(
            FIELD_RE % 'poster', webpage, 'thumbnail', fatal=False)
        timestamp = unified_timestamp(self._html_search_meta(
            'article:published_time', webpage, 'timestamp', fatal=False))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'formats': formats,
        }
