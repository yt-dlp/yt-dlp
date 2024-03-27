from urllib.parse import unquote
from .common import InfoExtractor
from ..utils import (
    unified_strdate,
    str_or_none,
    traverse_obj,
)


class MediciIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:medici|edu\.medici)\.tv/(?:(?:[a-zA-Z0-9-_\.]+)/)*(?:#!/)?(?P<id>[^?#&]+)'
    _TESTS = [
        {
            'url': 'https://www.medici.tv/en/operas/thomas-ades-the-exterminating-angel-calixto-bieito-opera-bastille-paris',
            'md5': 'd483f74e7a7a9eac0dbe152ab189050d',
            'info_dict': {
                'id': '8032',
                'ext': 'mp4',
                'title': 'Thomas Adès\'s The Exterminating Angel',
                'thumbnail': r're:^https?://medicitv-[abc]\.imgix\.net/movie/[^?]+\.jpg(?:\?[^?]+)?',
                'description': 'md5:708ae6350dadc604225b4a6e32482bab',
                'upload_date': '20240304',
            },
        },
        {
            'url': 'https://edu.medici.tv/en/operas/wagner-lohengrin-paris-opera-kirill-serebrennikov-piotr-beczala-kwangchul-youn-johanni-van-oostrum',
            'md5': '4ef3f4079a6e1c617584463a9eb84f99',
            'info_dict': {
                'id': '7900',
                'ext': 'mp4',
                'title': 'Wagner\'s Lohengrin',
                'thumbnail': r're:^https?://medicitv-[abc]\.imgix\.net/movie/[^?]+\.jpg(?:\?[^?]+)?',
                'description': 'md5:a384a62937866101f86902f21752cd89',
                'upload_date': '20231017',
            },
        },
        {
            'url': 'https://edu.medici.tv/en/concerts/pierre-laurent-aimard-plays-piano-fantasies-mozart-sweelinck-volkonski-bach-beethoven-benjamin',
            'md5': 'edc8564a7d2921f1ab702e3b7c917437',
            'info_dict': {
                'id': '7373',
                'ext': 'mp4',
                'title': 'Pierre-Laurent Aimard plays Mozart, Sweelinck, Volkonski, Bach, Beethoven, and Benjamin',
                'thumbnail': r're:^https?://medicitv-[abc]\.imgix\.net/movie/[^?]+\.jpg(?:\?[^?]+)?',
                'description': 'md5:3b61238577aa27eacf12d660a333c850',
                'upload_date': '20240323',
            },
        },
        {
            'url': 'https://www.medici.tv/en/ballets/carmen-ballet-choregraphie-de-jiri-bubenicek-teatro-dellopera-di-roma',
            'md5': '40f5e76cb701a97a6d7ba23b62c49990',
            'info_dict': {
                'id': '7857',
                'ext': 'mp4',
                'title': 'Carmen by Jiří Bubeníček after Roland Petit, music by Bizet, de Falla, Castelnuovo-Tedesco, and Bonolis',
                'thumbnail': r're:^https?://medicitv-[abc]\.imgix\.net/movie/[^?]+\.jpg(?:\?[^?]+)?',
                'description': 'md5:0f15a15611ed748020c769873e10a8bb',
                'upload_date': '20240223',
            },
        },
        {
            'url': 'https://www.medici.tv/en/documentaries/la-sonnambula-liege-2023-documentaire',
            'md5': '87ff198018ce79a34757ab0dd6f21080',
            'info_dict': {
                'id': '7513',
                'ext': 'mp4',
                'title': 'NEW: La Sonnambula',
                'thumbnail': r're:^https?://medicitv-[abc]\.imgix\.net/movie/[^?]+\.jpg(?:\?[^?]+)?',
                'description': 'md5:0caf9109a860fd50cd018df062a67f34',
                'upload_date': '20231103',
            },
        },
        {
            'url': 'https://edu.medici.tv/en/masterclasses/yvonne-loriod-olivier-messiaen',
            'md5': '5737b5b4d50a842605f5f7db6b76bce2',
            'info_dict': {
                'id': '3024',
                'ext': 'mp4',
                'title': 'Olivier Messiaen and Yvonne Loriod, pianists and teachers',
                'thumbnail': r're:^https?://medicitv-[abc]\.imgix\.net/movie/[^?]+\.jpg(?:\?[^?]+)?',
                'description': 'md5:aab948e2f7690214b5c28896c83f1fc1',
                'upload_date': '20150223',
            },
        },
        {
            'url': 'https://www.medici.tv/en/jazz/makaya-mccraven-la-rochelle',
            'md5': '4cc279a8b06609782747c8f50beea2b3',
            'info_dict': {
                'id': '7922',
                'ext': 'mp4',
                'title': 'NEW: Makaya McCraven in La Rochelle',
                'thumbnail': r're:^https?://medicitv-[abc]\.imgix\.net/movie/[^?]+\.jpg(?:\?[^?]+)?',
                'description': 'md5:b5a8aaeb6993d8ccb18bde8abb8aa8d2',
                'upload_date': '20231228',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        self._download_webpage(url, video_id)
        cookies = self._get_cookies(url)

        if "edu" in url:
            request_url = f'https://api.medici.tv/edu-satie/edito/movie-file/{video_id}/'
            source_url = 'https://edu.medici.tv'
        else:
            request_url = f'https://api.medici.tv/satie/edito/movie-file/{video_id}/'
            source_url = 'https://www.medici.tv'

        mAuth_cookie = cookies.get('auth._token.mAuth')
        if not mAuth_cookie:
            self.to_screen('[auth] Can\'t find a token for authorization. Only previews may be downloaded.')
            token = ''
        else:
            token = unquote(str_or_none(mAuth_cookie.value, ''))

        data = self._download_json(
            request_url, video_id,
            headers={
                'Authorization': token,
                'Device-Type': 'web',
                'Origin': source_url,
                'Referer': source_url + '/',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en',
            }
        )

        id = str_or_none(data.get('id'))
        title = data.get('title')
        description = data.get('subtitle')

        m3u8_url = traverse_obj(data, ('video', 'video_url'), expected_type=str)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, ext='mp4')

        thumbnail = data.get('picture')
        upload_date = unified_strdate(data.get('date_publish'))

        return {
            'id': id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'formats': formats,
            'subtitles': subtitles,
        }
