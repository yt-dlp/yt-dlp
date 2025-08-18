import re
import urllib.parse

from .common import InfoExtractor
from ..utils import js_to_json, url_or_none
from ..utils.traversal import traverse_obj


class FaulioLiveIE(InfoExtractor):
    _DOMAINS = (
        'aloula.sba.sa',
        'bahry.com',
        'maraya.sba.net.ae',
        'sat7plus.org',
    )
    _VALID_URL = fr'https?://(?:{"|".join(map(re.escape, _DOMAINS))})/(?:(?:en|ar|fa)/)?live/(?P<id>[a-zA-Z0-9-]+)'
    _TESTS = [{
        'url': 'https://aloula.sba.sa/live/saudiatv',
        'info_dict': {
            'id': 'aloula.faulio.com_saudiatv',
            'title': str,
            'description': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://bahry.com/live/1',
        'info_dict': {
            'id': 'bahry.faulio.com_1',
            'title': str,
            'description': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://maraya.sba.net.ae/live/1',
        'info_dict': {
            'id': 'maraya.faulio.com_1',
            'title': str,
            'description': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://sat7plus.org/live/pars',
        'info_dict': {
            'id': 'sat7.faulio.com_pars',
            'title': str,
            'description': str,
            'ext': 'mp4',
            'live_status': 'is_live',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://sat7plus.org/fa/live/arabic',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        config_data = self._search_json(
            r'window\.__NUXT__\.config=', webpage, 'config', video_id, transform_source=js_to_json)
        api_base = config_data['public']['TRANSLATIONS_API_URL']

        channel = traverse_obj(
            self._download_json(f'{api_base}/channels', video_id),
            (lambda k, v: v['url'] == video_id, any))

        formats = []
        subtitles = {}
        if hls_url := traverse_obj(channel, ('streams', 'hls', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                hls_url, video_id, 'mp4', m3u8_id='hls', live=True, fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        if mpd_url := traverse_obj(channel, ('streams', 'mpd', {url_or_none})):
            fmts, subs = self._extract_mpd_formats_and_subtitles(
                mpd_url, video_id, mpd_id='dash', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': f'{urllib.parse.urlparse(api_base).hostname}_{video_id}',
            **traverse_obj(channel, {
                'title': ('title', {str}),
                'description': ('description', {str}),
            }),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
        }
