from .common import ExtractorError, InfoExtractor
from ..networking import HEADRequest
from ..utils import random_uuidv4, traverse_obj


class FujiTVFODPlus7IE(InfoExtractor):
    _VALID_URL = r'https?://fod\.fujitv\.co\.jp/title/(?P<sid>[0-9a-z]{4})/(?P<id>[0-9a-z]+)'
    _API_URL = 'https://i.fod.fujitv.co.jp'
    _FRONTEND_URL = 'https://fod.fujitv.co.jp'
    _AUTH_API = 'https://fod.fujitv.co.jp/apps/api/1/auth/contents/web'
    _IMG_BASE = 'https://i.fod.fujitv.co.jp/img/program'
    _BITRATE_MAP = {
        300: (320, 180),
        800: (640, 360),
        1200: (1280, 720),
        2000: (1280, 720),
        4000: (1920, 1080),
    }

    _TESTS = [
        {
            'url': 'https://fod.fujitv.co.jp/title/5d40/5d40110076',
            'info_dict': {
                'id': '5d40110076',
                'ext': 'ts',
                'title': '#1318 『まる子、まぼろしの洋館を見る』の巻',
                'series': 'ちびまる子ちゃん',
                'series_id': '5d40',
                'description': 'md5:b3f51dbfdda162ac4f789e0ff4d65750',
                'thumbnail': 'https://i.fod.fujitv.co.jp/img/program/5d40/episode/5d40110076_a.jpg',
            },
        },
        {
            'url': 'https://fod.fujitv.co.jp/title/5d40/5d40810083',
            'info_dict': {
                'id': '5d40810083',
                'ext': 'ts',
                'title': '#1324 『まる子とオニの子』の巻／『結成！2月をムダにしない会』の巻',
                'description': 'md5:3972d900b896adc8ab1849e310507efa',
                'series': 'ちびまる子ちゃん',
                'series_id': '5d40',
                'thumbnail': 'https://i.fod.fujitv.co.jp/img/program/5d40/episode/5d40810083_a.jpg',
            },
            'skip': 'Video available only in one week',
        },
    ]

    def _real_extract(self, url):
        series_id, video_id = self._match_valid_url(url).groups()
        self._request_webpage(HEADRequest(self._FRONTEND_URL), video_id)
        token = None
        cookies = self._get_cookies(self._FRONTEND_URL)
        if cookies and 'CT' in cookies:
            token = cookies['CT']['value']
        if not token:
            # Fallback: try to fetch from HTML if needed (rare)
            front_page = self._download_webpage(
                self._FRONTEND_URL, video_id, note='Downloading front page for CT token', fatal=False,
            )
            token = self._search_regex(r'CT=([^;]+);', front_page or '', 'ct token', default=None)
        if not token:
            raise ExtractorError('CT token not found')

        json_response = self._download_json(
            f'{self._API_URL}/apps/api/c/v2/lineup/detail/',
            series_id,
            headers={'x-authorization': f'Bearer {token}'},
            query={'is_premium': 'false', 'lu_id': series_id},
        )

        episode = traverse_obj(json_response, ('episodes', lambda _, v: str(v.get('ep_id')) == video_id, any))
        if not episode:
            self.report_warning(f'Unable to find episode {video_id} in series {series_id}')

        json_response = self._download_json(
            f'{self._API_URL}/apps/api/c/v2/episode/detail/',
            series_id,
            headers={'x-authorization': f'Bearer {token}'},
            query={'is_premium': 'false', 'lu_id': series_id, 'ep_id': video_id},
        )


        detail = json_response
        # UA must be set to Android TV to get the settings URL otherwise, the URL wont appear
        # We dont know which UA is required to get the `android_tv` URL (if we manage to find out, we can use it here)
        settings_json = self._download_json(
            'https://fod.fujitv.co.jp/apps/api/1/auth/contents/web',video_id,
            headers={
                'x-authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 9; SHIELD Android TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36',
            },
            query={
                'site_id': 'fodapp',
                'ep_id': video_id,
                'qa': 'high',
                'uuid': random_uuidv4(),
                'starttime': 0,
                'is_pt': 'true',
            },
        )
        if not settings_json or 'settings' not in settings_json:
            raise ExtractorError('Unable to fetch video settings')

        # We dont know which UA is required to get the `android_tv` URL
        # as closest we can get is `sp_android` so we replace it with `tv_android` in the URL
        settings_url = settings_json['settings'].replace('sp_android', 'tv_android')

        video_selector_json = self._download_json(
            # UA must be set to Android TV to get the settings URL
            settings_url,
            video_id,
            headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 9; SHIELD Android TV)'},
            fatal=False,
        )

        m3u8_url = traverse_obj(video_selector_json, ('video_selector', -1, 'url'))

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, ext=None, m3u8_id='hls', fatal=False,
        )

        return {
            'id': video_id,
            'title': episode.get('ep_title') or detail.get('lu_title'),
            'series': detail.get('lu_title'),
            'series_id': series_id,
            'description': episode.get('ep_description') or detail.get('lu_description'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': f'{self._IMG_BASE}/{series_id}/episode/{video_id}_a.jpg',
        }
