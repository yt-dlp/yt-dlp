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

        episode = traverse_obj(json_response, ('episodes', lambda _, v: str(v.get('ep_id')) == video_id))
        if not episode:
            self.report_warning(f'Unable to find episode {video_id} in series {series_id}')

        json_response = self._download_json(
            f'{self._API_URL}/apps/api/c/v2/episode/detail/',
            series_id,
            headers={'x-authorization': f'Bearer {token}'},
            query={'is_premium': 'false', 'lu_id': series_id, 'ep_id': video_id},
        )

        '''
        {
            'ep_id': '5d40810269',
            'lu_id': '5d40',
            'lu_title': 'ちびまる子ちゃん',
            'subtitle_options': [
                {
                    'ep_id': '5d40810269',
                    'subtitle_option': 'normal',
                    'ep_title': '第1500話 『川田さんのライバル現る』の巻／『山根、月のパワーにあやかりたい』の巻',
                    'ep_hash_id': '160a8cf865c71879f90623298c3eaffcavod'
                }
            ],
            'coin': 0,
            'price': 0,
            'ep_title': '第1500話 『川田さんのライバル現る』の巻／『山根、月のパワーにあやかりたい』の巻',
            'ep_no': 2660,
            'disp_ep_no': '第1500話',
            'duration': '24分',
            'broadcast_end': '2025-10-12T18:00:00+09:00',
            'ep_description': '歩いていたまる子とたまちゃんは巴川の掃除をしている川田さんを見かけて声をかける。最近ゴミが少ないらしく、誰か他にも掃除してくれている人がいるのかもしれないと話す川田さん。そんな人が他にもいるのだろうかと疑問に思うまる子たちだが、翌日学校で、川田さんじゃない人が川掃除をしているのを見たという話を聞く。／もうすぐ十五夜。山根は、お母さんが月見団子を作ってくれるというので、いっぱい食べられるように胃腸を鍛えなくちゃと張り切っている。翌日の学校でも、月の話をしているまる子と山根たち。月といえば月見ということで、まる子たちは色んな月見料理を試してみることに。',
            'packs': [],
            'persons': [
                {
                    'person_id': 'W08-0850',
                    'person_name': '菊池　こころ'
                },
                {
                    'person_id': 'M93-1621',
                    'person_name': '島田　敏'
                },
                {
                    'person_id': 'M93-3530',
                    'person_name': '屋良　有作'
                },
                {
                    'person_id': 'SMB-003727',
                    'person_name': '一龍斎　貞友'
                },
                {
                    'person_id': 'SMB-048951',
                    'person_name': '佐々木　優子'
                },
                {
                    'person_id': 'W07-1492',
                    'person_name': '豊嶋　真千子'
                },
                {
                    'person_id': 'W93-3313',
                    'person_name': '渡辺　菜生子'
                },
                {
                    'person_id': 'M04-0312',
                    'person_name': '菊池　正美'
                },
                {
                    'person_id': 'M93-2251',
                    'person_name': '飛田　展男'
                },
                {
                    'person_id': 'SMB-070004',
                    'person_name': '田野　めぐみ'
                },
                {
                    'person_id': 'SMB-070005',
                    'person_name': 'カシワクラツトム'
                },
                {
                    'person_id': 'W93-2156',
                    'person_name': 'ならはし　みき'
                },
                {
                    'person_id': 'M93-2118',
                    'person_name': '茶風林'
                },
                {
                    'person_id': 'W93-2004',
                    'person_name': '中　友子'
                },
                {
                    'person_id': 'SMB-135480',
                    'person_name': '本井　えみ'
                },
                {
                    'person_id': 'M98-0260',
                    'person_name': '陶山　章央'
                },
                {
                    'person_id': 'W96-0379',
                    'person_name': '永澤　菜教'
                },
                {
                    'person_id': 'M09-1345',
                    'person_name': '沼田　祐介'
                },
                {
                    'person_id': 'W00-0610',
                    'person_name': '真山　亜子'
                },
                {
                    'person_id': 'SMB-089907',
                    'person_name': '木村　匡也'
                }
            ],
            'share_url': 'https://fod.fujitv.co.jp/title/5d40/5d40810269/',
            'sales_type': [
                'plus7'
            ],
            'is_teaser': false,
            'is_live': false,
            'is_download': false,
            'is_sold_together': false,
            'is_vm': false,
            'genre': {
                'genre_id': 'AN',
                'genre_name': 'アニメ',
                'genre_eng_name': 'anime'
            },
            'minogashi_pairing_ep_id': '5d40110269',
            'ep_release_date': '2025-10-05T18:30:00+09:00',
            'ppv_status': 'none',
            'priority_number': 2660,
            'sort_number': 2660,
            'purchase_end': '2025-10-12T18:00:00+09:00',
            'ep_hash_id': '160a8cf865c71879f90623298c3eaffcavod',
            'is_lite_course_lock': false
        }
        '''

        detail = json_response
        # UA must be set to Android TV to get the settings URL otherwise, the URL wont appear
        # We dont know which UA is required to get the `android_tv` URL (if we manage to find out, we can use it here)
        settings_json = self._download_json(
            self._AUTH_API,
            video_id,
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
            '_format_sort_fields': ('tbr',),
        }
