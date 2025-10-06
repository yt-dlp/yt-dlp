from .common import InfoExtractor
from ..networking import HEADRequest


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

    _TESTS = [{
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
    }, {
        'url': 'https://fod.fujitv.co.jp/title/5d40/5d40810083',
        'info_dict': {
            'id': '5d40810083',
            'ext': 'ts',
            'title': '#1324 『まる子とオニの子』の巻／『結成！2月をムダにしない会』の巻',
            'description': 'md5:3972d900b896adc8ab1849e310507efa',
            'series': 'ちびまる子ちゃん',
            'series_id': '5d40',
            'thumbnail': 'https://i.fod.fujitv.co.jp/img/program/5d40/episode/5d40810083_a.jpg'},
        'skip': 'Video available only in one week',
    }]

    def _real_extract(self, url):
        import random, string
        series_id, video_id = self._match_valid_url(url).groups()
        # 1. 取得 CT token
        front_page = self._download_webpage(
            self._FRONTEND_URL, video_id, note='Downloading front page for CT token', fatal=False)
        token = None
        # 嘗試從 cookie 取得 CT
        cookies = self._get_cookies(self._FRONTEND_URL)
        if cookies and 'CT' in cookies:
            token = cookies['CT']['value']
        if not token:
            # 從 HTML 嘗試正則抓取
            token = self._search_regex(r'CT=([^;]+);', front_page or '', 'ct token', default=None)
        if not token:
            raise self.raise_no_formats('Unable to get CT token; login/cookies may be required')

        # 2. 取得節目資訊
        api_url = f'{self._API_URL}/apps/api/c/v2/lineup/detail/?lu_id={series_id}&is_premium=false'
        json_response = self._download_json(
            api_url, series_id, headers={'x-authorization': f'Bearer {token}'}, fatal=False)
        if not json_response:
            raise self.raise_no_formats('API response is empty, site structure may have changed')

        episodes = json_response.get('episodes') or []
        detail = json_response.get('detail') or {}
        episode = next((ep for ep in episodes if str(ep.get('ep_id')) == video_id), None)
        if not episode:
            raise self.raise_no_formats('Episode not found in API response')

        # 3. 取得 settings_url (授權)
        uuid = ''.join(random.choices(string.ascii_lowercase + string.digits, k=36))
        site_id = 'fodapp'
        auth_url = (f'{self._AUTH_API}?'
                    f'site_id={site_id}&ep_id={video_id}&qa=high&uuid={uuid}&starttime=0&is_pt=true')
        settings_json = self._download_json(
            auth_url, video_id, headers={
                'x-authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 9; SHIELD Android TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36'
            }, fatal=False)
        if not settings_json or 'settings' not in settings_json:
            raise self.raise_no_formats('Failed to get settings url')
        settings_url = settings_json['settings'].replace('sp_android', 'tv_android')

        # 4. 取得 m3u8 url
        video_selector_json = self._download_json(
            settings_url, video_id, headers={'User-Agent': 'Mozilla/5.0 (Linux; Android 9; SHIELD Android TV)'}, fatal=False)
        if not video_selector_json or 'video_selector' not in video_selector_json:
            raise self.raise_no_formats('Failed to get video selector')
        video_selector = video_selector_json['video_selector']
        # video_selector 可能是 list
        if isinstance(video_selector, list):
            m3u8_url = video_selector[-1]['url']
        else:
            m3u8_url = video_selector

        # 5. 解析格式
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, ext=None, m3u8_id='hls', fatal=False)

        return {
            'id': video_id,
            'title': episode.get('ep_title') or detail.get('lu_title'),
            'series': detail.get('lu_title'),
            'series_id': series_id,
            'description': episode.get('ep_description') or detail.get('lu_description'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': f'{self._IMG_BASE}/{series_id}/episode/{video_id}_a.jpg',
            '_format_sort_fields': ('tbr', ),
        }
