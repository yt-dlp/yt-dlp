from .common import InfoExtractor
from ..compat import compat_str
from ..networking.exceptions import HTTPError
from ..utils import (
    extract_attributes,
    try_get,
    urlencode_postdata,
    ExtractorError,
)


class TVPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tvplayer\.com/watch/(?P<id>[^/?#]+)'
    _TEST = {
        'url': 'http://tvplayer.com/watch/bbcone',
        'info_dict': {
            'id': '89',
            'ext': 'mp4',
            'title': r're:^BBC One [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        current_channel = extract_attributes(self._search_regex(
            r'(<div[^>]+class="[^"]*current-channel[^"]*"[^>]*>)',
            webpage, 'channel element'))
        title = current_channel['data-name']

        resource_id = current_channel['data-id']

        token = self._search_regex(
            r'data-token=(["\'])(?P<token>(?!\1).+)\1', webpage,
            'token', group='token')

        context = self._download_json(
            'https://tvplayer.com/watch/context', display_id,
            'Downloading JSON context', query={
                'resource': resource_id,
                'gen': token,
            })

        validate = context['validate']
        platform = try_get(
            context, lambda x: x['platform']['key'], compat_str) or 'firefox'

        try:
            response = self._download_json(
                'http://api.tvplayer.com/api/v2/stream/live',
                display_id, 'Downloading JSON stream', headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                }, data=urlencode_postdata({
                    'id': resource_id,
                    'service': 1,
                    'platform': platform,
                    'validate': validate,
                }))['tvplayer']['response']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                response = self._parse_json(
                    e.cause.response.read().decode(), resource_id)['tvplayer']['response']
                raise ExtractorError(
                    '%s said: %s' % (self.IE_NAME, response['error']), expected=True)
            raise

        formats = self._extract_m3u8_formats(response['stream'], display_id, 'mp4')

        return {
            'id': resource_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'is_live': True,
        }
