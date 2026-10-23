from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    make_archive_id,
    parse_qs,
    time_seconds,
)
from ..utils.traversal import traverse_obj


class UlizaPlayerIE(InfoExtractor):
    _VALID_URL = r'https://player-api\.p\.uliza\.jp/v1/players/[^?#]+\?(?:[^#]*&)?name=(?P<id>[^#&]+)'
    _TESTS = [{
        'url': 'https://player-api.p.uliza.jp/v1/players/timeshift-disabled/pia/admin?type=normal&playerobjectname=ulizaPlayer&name=livestream01_dvr&repeatable=true',
        'info_dict': {
            'id': '88f3109a-f503-4d0f-a9f7-9f39ac745d84',
            'ext': 'mp4',
            'title': '88f3109a-f503-4d0f-a9f7-9f39ac745d84',
            'live_status': 'was_live',
            '_old_archive_ids': ['piaulizaportal 88f3109a-f503-4d0f-a9f7-9f39ac745d84'],
        },
    }, {
        'url': 'https://player-api.p.uliza.jp/v1/players/uliza_jp_gallery_normal/promotion/admin?type=presentation&name=cookings&targetid=player1',
        'info_dict': {
            'id': 'ae350126-5e22-4a7f-a8ac-8d0fd448b800',
            'ext': 'mp4',
            'title': 'ae350126-5e22-4a7f-a8ac-8d0fd448b800',
            'live_status': 'not_live',
            '_old_archive_ids': ['piaulizaportal ae350126-5e22-4a7f-a8ac-8d0fd448b800'],
        },
    }, {
        'url': 'https://player-api.p.uliza.jp/v1/players/default-player/pia/admin?type=normal&name=pia_movie_uliza_fix&targetid=ulizahtml5&repeatable=true',
        'info_dict': {
            'id': '0644ecc8-e354-41b4-b957-3b08a2d63df1',
            'ext': 'mp4',
            'title': '0644ecc8-e354-41b4-b957-3b08a2d63df1',
            'live_status': 'not_live',
            '_old_archive_ids': ['piaulizaportal 0644ecc8-e354-41b4-b957-3b08a2d63df1'],
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        player_data = self._download_webpage(
            url, display_id, headers={'Referer': 'https://player-api.p.uliza.jp/'},
            note='Fetching player data', errnote='Unable to fetch player data')

        m3u8_url = self._search_regex(
            r'["\'](https://vms-api\.p\.uliza\.jp/v1/prog-index\.m3u8[^"\']+)', player_data, 'm3u8 url')
        video_id = parse_qs(m3u8_url).get('ss', [display_id])[0]

        formats = self._extract_m3u8_formats(m3u8_url, video_id)
        m3u8_type = self._search_regex(
            r'/hls/(dvr|video)/', traverse_obj(formats, (0, 'url')), 'm3u8 type', default=None)
        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
            'live_status': {
                'video': 'is_live',
                'dvr': 'was_live',  # short-term archives
            }.get(m3u8_type, 'not_live'),  # VOD or long-term archives
            '_old_archive_ids': [make_archive_id('PIAULIZAPortal', video_id)],
        }


class UlizaPortalIE(InfoExtractor):
    IE_DESC = 'ulizaportal.jp'
    _VALID_URL = r'https?://(?:www\.)?ulizaportal\.jp/pages/(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})'
    _TESTS = [{
        'url': 'https://ulizaportal.jp/pages/005f18b7-e810-5618-cb82-0987c5755d44',
        'info_dict': {
            'id': 'ae350126-5e22-4a7f-a8ac-8d0fd448b800',
            'display_id': '005f18b7-e810-5618-cb82-0987c5755d44',
            'title': 'プレゼンテーションプレイヤーのサンプル',
            'live_status': 'not_live',
            '_old_archive_ids': ['piaulizaportal ae350126-5e22-4a7f-a8ac-8d0fd448b800'],
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://ulizaportal.jp/pages/005e1b23-fe93-5780-19a0-98e917cc4b7d?expires=4102412400&signature=f422a993b683e1068f946caf406d211c17d1ef17da8bef3df4a519502155aa91&version=1',
        'info_dict': {
            'id': '0644ecc8-e354-41b4-b957-3b08a2d63df1',
            'display_id': '005e1b23-fe93-5780-19a0-98e917cc4b7d',
            'title': '【確認用】視聴サンプルページ（ULIZA）',
            'live_status': 'not_live',
            '_old_archive_ids': ['piaulizaportal 0644ecc8-e354-41b4-b957-3b08a2d63df1'],
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
            raise ExtractorError('The link is expired', video_id=video_id, expected=True)

        webpage = self._download_webpage(url, video_id)

        player_data_url = self._search_regex(
            r'<script [^>]*\bsrc="(https://player-api\.p\.uliza\.jp/v1/players/[^"]+)"',
            webpage, 'player data url')
        return self.url_result(
            player_data_url, UlizaPlayerIE, url_transparent=True,
            display_id=video_id, video_title=self._html_extract_title(webpage))
