from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, parse_qs, smuggle_url, time_seconds, traverse_obj, unsmuggle_url


class PIAULIZAPortalAPIIE(InfoExtractor):
    IE_DESC = 'https://player-api.p.uliza.jp - PIA ULIZA m3u8'
    SCRIPT_TAG_REGEX_PATTERN = r'<script [^>]*\bsrc="(https://player-api\.p\.uliza\.jp/v1/players/[^"]+)"'

    _VALID_URL = r'https://player-api\.p\.uliza\.jp/v1/players/(?P<id>.*)'
    _TESTS = [
        {
            'url': 'https://player-api.p.uliza.jp/v1/players/timeshift-disabled/pia/admin?type=normal&playerobjectname=ulizaPlayer&name=livestream01_dvr&repeatable=true',
            'info_dict': {
                'id': 'timeshift-disabled/pia/admin?type=normal&playerobjectname=ulizaPlayer&name=livestream01_dvr&repeatable=true',
                'title': 'livestream01_dvr',
                'live_status': 'was_live',
            },
            'params': {
                'skip_download': True,
                'ignore_no_formats_error': True,
            },
        },
        {
            'url': 'https://player-api.p.uliza.jp/v1/players/uliza_jp_gallery_normal/promotion/admin?type=presentation&name=cookings&targetid=player1',
            'info_dict': {
                'id': 'uliza_jp_gallery_normal/promotion/admin?type=presentation&name=cookings&targetid=player1',
                'title': 'cookings',
                'live_status': 'not_live',
            },
            'params': {
                'skip_download': True,
                'ignore_no_formats_error': True,
            },
        },
        {
            'url': 'https://player-api.p.uliza.jp/v1/players/default-player/pia/admin?type=normal&name=pia_movie_uliza_fix&targetid=ulizahtml5&repeatable=true',
            'info_dict': {
                'id': 'default-player/pia/admin?type=normal&name=pia_movie_uliza_fix&targetid=ulizahtml5&repeatable=true',
                'title': 'pia_movie_uliza_fix',
                'live_status': 'not_live',
            },
            'params': {
                'skip_download': True,
                'ignore_no_formats_error': True,
            },
        },
    ]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = smuggled_data.get('video_id') or self._search_regex(r'&name=([^&]+)', self._match_id(url), 'video id')
        player_data = self._download_webpage(
            url,
            video_id,
            headers={'Referer': smuggled_data.get('referer') or 'https://player-api.p.uliza.jp/'},
            note='Fetching player data', errnote='Unable to fetch player data',
        )

        formats = self._extract_m3u8_formats(
            self._search_regex(
                r'["\'](https://vms-api\.p\.uliza\.jp/v1/prog-index\.m3u8[^"\']+)', player_data,
                'm3u8 url', default=None),
            video_id, fatal=False)
        m3u8_type = self._search_regex(
            r'/hls/(dvr|video)/', traverse_obj(formats, (0, 'url')), 'm3u8 type', default=None)
        return {
            'id': video_id,
            'title': smuggled_data.get('video_title') or video_id,
            'formats': formats,
            'live_status': {
                'video': 'is_live',
                'dvr': 'was_live',  # short-term archives
            }.get(m3u8_type, 'not_live'),  # VOD or long-term archives
            **smuggled_data.get('info_dict', {}),
        }


class PIAULIZAPortalIE(InfoExtractor):
    IE_DESC = 'ulizaportal.jp - PIA LIVE STREAM'
    _VALID_URL = r'https?://(?:www\.)?ulizaportal\.jp/pages/(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})'
    _TESTS = [{
        'url': 'https://ulizaportal.jp/pages/005f18b7-e810-5618-cb82-0987c5755d44',
        'info_dict': {
            'id': '005f18b7-e810-5618-cb82-0987c5755d44',
            'title': 'プレゼンテーションプレイヤーのサンプル',
            'live_status': 'not_live',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://ulizaportal.jp/pages/005e1b23-fe93-5780-19a0-98e917cc4b7d?expires=4102412400&signature=f422a993b683e1068f946caf406d211c17d1ef17da8bef3df4a519502155aa91&version=1',
        'info_dict': {
            'id': '005e1b23-fe93-5780-19a0-98e917cc4b7d',
            'title': '【確認用】視聴サンプルページ（ULIZA）',
            'live_status': 'not_live',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        expires = int_or_none(traverse_obj(parse_qs(url), ('expires', 0)))
        if expires and expires <= time_seconds():
            raise ExtractorError('The link is expired.', video_id=video_id, expected=True)

        webpage = self._download_webpage(url, video_id)

        player_data_url = self._search_regex(
            PIAULIZAPortalAPIIE.SCRIPT_TAG_REGEX_PATTERN,
            webpage, 'player data url')
        return self.url_result(
            smuggle_url(
                player_data_url,
                {'video_id': video_id, 'referer': 'https://ulizaportal.jp/', 'info_dict': {
                    'id': video_id,
                    'title': self._html_extract_title(webpage),
                }},
            ),
            ie=PIAULIZAPortalAPIIE.ie_key(),
        )
