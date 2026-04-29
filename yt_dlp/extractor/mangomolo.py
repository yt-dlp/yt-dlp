import base64
import urllib.parse

from .common import InfoExtractor
from ..utils import classproperty, int_or_none


class MangomoloBaseIE(InfoExtractor):
    _BASE_REGEX = r'(?:https?:)?//(?:admin\.mangomolo\.com/analytics/index\.php/customers/embed/|player\.mangomolo\.com/v1/)'
    _SLUG = None

    @classproperty
    def _VALID_URL(cls):
        return f'{cls._BASE_REGEX}{cls._SLUG}'

    @classproperty
    def _EMBED_REGEX(cls):
        return [rf'<iframe[^>]+src=(["\'])(?P<url>{cls._VALID_URL}.+?)\1']

    def _extract_from_webpage(self, url, webpage):
        for res in super()._extract_from_webpage(url, webpage):
            yield {
                **res,
                '_type': 'url_transparent',
                'id': self._search_regex(self._SLUG, res['url'], 'id', group='id'),
                'uploader': self._search_regex(r'^(?:https?://)?([^/]*)/.*', url, 'video uploader'),
            }

    def _get_real_id(self, page_id):
        return page_id

    def _real_extract(self, url):
        page_id = self._get_real_id(self._match_id(url))
        webpage = self._download_webpage(
            'https://player.mangomolo.com/v1/{}?{}'.format(self._TYPE, url.split('?')[1]), page_id)
        hidden_inputs = self._hidden_inputs(webpage)
        m3u8_entry_protocol = 'm3u8' if self._IS_LIVE else 'm3u8_native'

        format_url = self._html_search_regex(
            [
                r'(?:file|src)\s*:\s*"(https?://[^"]+?/playlist\.m3u8)',
                r'<a[^>]+href="(rtsp://[^"]+)"',
            ], webpage, 'format url')
        formats = self._extract_wowza_formats(
            format_url, page_id, m3u8_entry_protocol, ['smil'])

        return {
            'id': page_id,
            'title': page_id,
            'uploader_id': hidden_inputs.get('userid'),
            'duration': int_or_none(hidden_inputs.get('duration')),
            'is_live': self._IS_LIVE,
            'formats': formats,
        }


class MangomoloVideoIE(MangomoloBaseIE):
    _TYPE = 'video'
    IE_NAME = 'mangomolo:' + _TYPE
    _SLUG = r'video\?.*?\bid=(?P<id>\d+)'

    _IS_LIVE = False


class MangomoloLiveIE(MangomoloBaseIE):
    _TYPE = 'live'
    IE_NAME = 'mangomolo:' + _TYPE
    _SLUG = r'(?:live|index)\?.*?\bchannelid=(?P<id>(?:[A-Za-z0-9+/=]|%2B|%2F|%3D)+)'
    _IS_LIVE = True

    def _get_real_id(self, page_id):
        return base64.b64decode(urllib.parse.unquote(page_id)).decode()
