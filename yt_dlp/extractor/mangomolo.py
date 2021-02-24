# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_b64decode,
    compat_urllib_parse_unquote,
)
from ..utils import int_or_none


class MangomoloBaseIE(InfoExtractor):
    _BASE_REGEX = r'https?://(?:admin\.mangomolo\.com/analytics/index\.php/customers/embed/|player\.mangomolo\.com/v1/)'

    def _get_real_id(self, page_id):
        return page_id

    def _real_extract(self, url):
        page_id = self._get_real_id(self._match_id(url))
        webpage = self._download_webpage(
            'https://player.mangomolo.com/v1/%s?%s' % (self._TYPE, url.split('?')[1]), page_id)
        hidden_inputs = self._hidden_inputs(webpage)
        m3u8_entry_protocol = 'm3u8' if self._IS_LIVE else 'm3u8_native'

        format_url = self._html_search_regex(
            [
                r'(?:file|src)\s*:\s*"(https?://[^"]+?/playlist\.m3u8)',
                r'<a[^>]+href="(rtsp://[^"]+)"'
            ], webpage, 'format url')
        formats = self._extract_wowza_formats(
            format_url, page_id, m3u8_entry_protocol, ['smil'])
        self._sort_formats(formats)

        return {
            'id': page_id,
            'title': self._live_title(page_id) if self._IS_LIVE else page_id,
            'uploader_id': hidden_inputs.get('userid'),
            'duration': int_or_none(hidden_inputs.get('duration')),
            'is_live': self._IS_LIVE,
            'formats': formats,
        }


class MangomoloVideoIE(MangomoloBaseIE):
    _TYPE = 'video'
    IE_NAME = 'mangomolo:' + _TYPE
    _VALID_URL = MangomoloBaseIE._BASE_REGEX + r'video\?.*?\bid=(?P<id>\d+)'
    _IS_LIVE = False


class MangomoloLiveIE(MangomoloBaseIE):
    _TYPE = 'live'
    IE_NAME = 'mangomolo:' + _TYPE
    _VALID_URL = MangomoloBaseIE._BASE_REGEX + r'(live|index)\?.*?\bchannelid=(?P<id>(?:[A-Za-z0-9+/=]|%2B|%2F|%3D)+)'
    _IS_LIVE = True

    def _get_real_id(self, page_id):
        return compat_b64decode(compat_urllib_parse_unquote(page_id)).decode()
