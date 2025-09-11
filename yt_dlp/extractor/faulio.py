import re
import urllib.parse

from .common import InfoExtractor
from ..utils import int_or_none, js_to_json, url_or_none
from ..utils.traversal import traverse_obj


class FaulioBaseIE(InfoExtractor):
    _DOMAINS = (
        'aloula.sba.sa',
        'bahry.com',
        'maraya.sba.net.ae',
        'sat7plus.org',
    )
    _LANGUAGES = ('ar', 'en', 'fa')
    _BASE_URL_RE = fr'https?://(?:{"|".join(map(re.escape, _DOMAINS))})/(?:(?:{"|".join(_LANGUAGES)})/)?'

    def _get_headers(self, url):
        parsed_url = urllib.parse.urlparse(url)
        return {
            'Referer': url,
            'Origin': f'{parsed_url.scheme}://{parsed_url.hostname}',
        }

    def _get_api_base(self, url, video_id):
        webpage = self._download_webpage(url, video_id)
        config_data = self._search_json(
            r'window\.__NUXT__\.config=', webpage, 'config', video_id, transform_source=js_to_json)
        return config_data['public']['TRANSLATIONS_API_URL']


class FaulioIE(FaulioBaseIE):
    _VALID_URL = fr'{FaulioBaseIE._BASE_URL_RE}(?:episode|media)/(?P<id>[a-zA-Z0-9-]+)'
    _TESTS = [{
        'url': 'https://aloula.sba.sa/en/episode/29102',
        'info_dict': {
            'id': 'aloula.faulio.com_29102',
            'ext': 'mp4',
            'display_id': 'هذا-مكانك-03-004-v-29102',
            'title': 'الحلقة 4',
            'episode': 'الحلقة 4',
            'description': '',
            'series': 'هذا مكانك',
            'season': 'Season 3',
            'season_number': 3,
            'episode_number': 4,
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 4855,
            'age_limit': 3,
        },
    }, {
        'url': 'https://bahry.com/en/media/1191',
        'info_dict': {
            'id': 'bahry.faulio.com_1191',
            'ext': 'mp4',
            'display_id': 'Episode-4-1191',
            'title': 'Episode 4',
            'episode': 'Episode 4',
            'description': '',
            'series': 'Wild Water',
            'season': 'Season 1',
            'season_number': 1,
            'episode_number': 4,
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1653,
            'age_limit': 0,
        },
    }, {
        'url': 'https://maraya.sba.net.ae/episode/127735',
        'info_dict': {
            'id': 'maraya.faulio.com_127735',
            'ext': 'mp4',
            'display_id': 'عبدالله-الهاجري---عبدالرحمن-المطروشي-127735',
            'title': 'عبدالله الهاجري - عبدالرحمن المطروشي',
            'episode': 'عبدالله الهاجري - عبدالرحمن المطروشي',
            'description': 'md5:53de01face66d3d6303221e5a49388a0',
            'series': 'أبناؤنا في الخارج',
            'season': 'Season 3',
            'season_number': 3,
            'episode_number': 7,
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1316,
            'age_limit': 0,
        },
    }, {
        'url': 'https://sat7plus.org/episode/18165',
        'info_dict': {
            'id': 'sat7.faulio.com_18165',
            'ext': 'mp4',
            'display_id': 'ep-13-ADHD-18165',
            'title': 'ADHD and creativity',
            'episode': 'ADHD and creativity',
            'description': '',
            'series': 'ADHD Podcast',
            'season': 'Season 1',
            'season_number': 1,
            'episode_number': 13,
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2492,
            'age_limit': 0,
        },
    }, {
        'url': 'https://aloula.sba.sa/en/episode/0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_base = self._get_api_base(url, video_id)
        video_info = self._download_json(f'{api_base}/video/{video_id}', video_id, fatal=False)
        player_info = self._download_json(f'{api_base}/video/{video_id}/player', video_id)

        headers = self._get_headers(url)
        formats = []
        subtitles = {}
        if hls_url := traverse_obj(player_info, ('settings', 'protocols', 'hls', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                hls_url, video_id, 'mp4', m3u8_id='hls', fatal=False, headers=headers)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        if mpd_url := traverse_obj(player_info, ('settings', 'protocols', 'dash', {url_or_none})):
            fmts, subs = self._extract_mpd_formats_and_subtitles(
                mpd_url, video_id, mpd_id='dash', fatal=False, headers=headers)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': f'{urllib.parse.urlparse(api_base).hostname}_{video_id}',
            **traverse_obj(traverse_obj(video_info, ('blocks', 0)), {
                'display_id': ('slug', {str}),
                'title': ('title', {str}),
                'episode': ('title', {str}),
                'description': ('description', {str}),
                'series': ('program_title', {str}),
                'season_number': ('season_number', {int_or_none}),
                'episode_number': ('episode', {int_or_none}),
                'thumbnail': ('image', {url_or_none}),
                'duration': ('duration', 'total', {int_or_none}),
                'age_limit': ('age_rating', {int_or_none}),
            }),
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': headers,
        }


class FaulioLiveIE(FaulioBaseIE):
    _VALID_URL = fr'{FaulioBaseIE._BASE_URL_RE}live/(?P<id>[a-zA-Z0-9-]+)'
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
        api_base = self._get_api_base(url, video_id)

        channel = traverse_obj(
            self._download_json(f'{api_base}/channels', video_id),
            (lambda k, v: v['url'] == video_id, any))

        headers = self._get_headers(url)
        formats = []
        subtitles = {}
        if hls_url := traverse_obj(channel, ('streams', 'hls', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                hls_url, video_id, 'mp4', m3u8_id='hls', live=True, fatal=False, headers=headers)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        if mpd_url := traverse_obj(channel, ('streams', 'mpd', {url_or_none})):
            fmts, subs = self._extract_mpd_formats_and_subtitles(
                mpd_url, video_id, mpd_id='dash', fatal=False, headers=headers)
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
            'http_headers': headers,
            'is_live': True,
        }
