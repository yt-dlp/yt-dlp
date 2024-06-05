import urllib.parse

from .common import InfoExtractor
from ..utils import (
    filter_dict,
    parse_iso8601,
    traverse_obj,
    try_call,
    url_or_none,
)


class MediciIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?P<sub>www|edu)\.)?medici\.tv/[a-z]{2}/[\w.-]+/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.medici.tv/en/operas/thomas-ades-the-exterminating-angel-calixto-bieito-opera-bastille-paris',
        'md5': 'd483f74e7a7a9eac0dbe152ab189050d',
        'info_dict': {
            'id': '8032',
            'ext': 'mp4',
            'title': 'Thomas Adès\'s The Exterminating Angel',
            'description': 'md5:708ae6350dadc604225b4a6e32482bab',
            'thumbnail': r're:https://.+/.+\.jpg',
            'upload_date': '20240304',
            'timestamp': 1709561766,
            'display_id': 'thomas-ades-the-exterminating-angel-calixto-bieito-opera-bastille-paris',
        },
        'expected_warnings': [r'preview'],
    }, {
        'url': 'https://edu.medici.tv/en/operas/wagner-lohengrin-paris-opera-kirill-serebrennikov-piotr-beczala-kwangchul-youn-johanni-van-oostrum',
        'md5': '4ef3f4079a6e1c617584463a9eb84f99',
        'info_dict': {
            'id': '7900',
            'ext': 'mp4',
            'title': 'Wagner\'s Lohengrin',
            'description': 'md5:a384a62937866101f86902f21752cd89',
            'thumbnail': r're:https://.+/.+\.jpg',
            'upload_date': '20231017',
            'timestamp': 1697554771,
            'display_id': 'wagner-lohengrin-paris-opera-kirill-serebrennikov-piotr-beczala-kwangchul-youn-johanni-van-oostrum',
        },
        'expected_warnings': [r'preview'],
    }, {
        'url': 'https://www.medici.tv/en/concerts/sergey-smbatyan-conducts-mansurian-chouchane-siranossian-mario-brunello',
        'md5': '9dd757e53b22b2511e85ea9ea60e4815',
        'info_dict': {
            'id': '5712',
            'ext': 'mp4',
            'title': 'Sergey Smbatyan conducts Tigran Mansurian — With Chouchane Siranossian and Mario Brunello',
            'thumbnail': r're:https://.+/.+\.jpg',
            'description': 'md5:9411fe44c874bb10e9af288c65816e41',
            'upload_date': '20200323',
            'timestamp': 1584975600,
            'display_id': 'sergey-smbatyan-conducts-mansurian-chouchane-siranossian-mario-brunello',
        },
        'expected_warnings': [r'preview'],
    }, {
        'url': 'https://www.medici.tv/en/ballets/carmen-ballet-choregraphie-de-jiri-bubenicek-teatro-dellopera-di-roma',
        'md5': '40f5e76cb701a97a6d7ba23b62c49990',
        'info_dict': {
            'id': '7857',
            'ext': 'mp4',
            'title': 'Carmen by Jiří Bubeníček after Roland Petit, music by Bizet, de Falla, Castelnuovo-Tedesco, and Bonolis',
            'thumbnail': r're:https://.+/.+\.jpg',
            'description': 'md5:0f15a15611ed748020c769873e10a8bb',
            'upload_date': '20240223',
            'timestamp': 1708707600,
            'display_id': 'carmen-ballet-choregraphie-de-jiri-bubenicek-teatro-dellopera-di-roma',
        },
        'expected_warnings': [r'preview'],
    }, {
        'url': 'https://www.medici.tv/en/documentaries/la-sonnambula-liege-2023-documentaire',
        'md5': '87ff198018ce79a34757ab0dd6f21080',
        'info_dict': {
            'id': '7513',
            'ext': 'mp4',
            'title': 'La Sonnambula',
            'thumbnail': r're:https://.+/.+\.jpg',
            'description': 'md5:0caf9109a860fd50cd018df062a67f34',
            'upload_date': '20231103',
            'timestamp': 1699010830,
            'display_id': 'la-sonnambula-liege-2023-documentaire',
        },
        'expected_warnings': [r'preview'],
    }, {
        'url': 'https://edu.medici.tv/en/masterclasses/yvonne-loriod-olivier-messiaen',
        'md5': 'fb5dcec46d76ad20fbdbaabb01da191d',
        'info_dict': {
            'id': '3024',
            'ext': 'mp4',
            'title': 'Olivier Messiaen and Yvonne Loriod, pianists and teachers',
            'thumbnail': r're:https://.+/.+\.jpg',
            'description': 'md5:aab948e2f7690214b5c28896c83f1fc1',
            'upload_date': '20150223',
            'timestamp': 1424706608,
            'display_id': 'yvonne-loriod-olivier-messiaen',
        },
        'skip': 'Requires authentication; preview starts in the middle',
    }, {
        'url': 'https://www.medici.tv/en/jazz/makaya-mccraven-la-rochelle',
        'md5': '4cc279a8b06609782747c8f50beea2b3',
        'info_dict': {
            'id': '7922',
            'ext': 'mp4',
            'title': 'NEW: Makaya McCraven in La Rochelle',
            'thumbnail': r're:https://.+/.+\.jpg',
            'description': 'md5:b5a8aaeb6993d8ccb18bde8abb8aa8d2',
            'upload_date': '20231228',
            'timestamp': 1703754863,
            'display_id': 'makaya-mccraven-la-rochelle',
        },
        'expected_warnings': [r'preview'],
    }]

    def _real_extract(self, url):
        display_id, subdomain = self._match_valid_url(url).group('id', 'sub')
        self._request_webpage(url, display_id, 'Requesting CSRF token cookie')

        subdomain = 'edu-' if subdomain == 'edu' else ''
        origin = f'https://{urllib.parse.urlparse(url).hostname}'

        data = self._download_json(
            f'https://api.medici.tv/{subdomain}satie/edito/movie-file/{display_id}/', display_id,
            headers=filter_dict({
                'Authorization': try_call(
                    lambda: urllib.parse.unquote(self._get_cookies(url)['auth._token.mAuth'].value)),
                'Device-Type': 'web',
                'Origin': origin,
                'Referer': f'{origin}/',
                'Accept': 'application/json, text/plain, */*',
            }))

        if not traverse_obj(data, ('video', 'is_full_video')) and traverse_obj(
                data, ('video', 'is_limited_by_user_access')):
            self.report_warning(
                'The full video is for subscribers only. Only previews will be downloaded. If you '
                'have used the --cookies-from-browser option, try using the --cookies option instead')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            data['video']['video_url'], display_id, 'mp4')

        return {
            'id': str(data['id']),
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('subtitle', {str}),
                'thumbnail': ('picture', {url_or_none}),
                'timestamp': ('date_publish', {parse_iso8601}),
            }),
        }
