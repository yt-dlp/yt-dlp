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
                'thumbnail': r're:^https?://medicitv-a\.imgix\.net/movie/[^?]+\.jpg(?:\?[^?]+)?',
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
                'thumbnail': r're:^https?://medicitv-a\.imgix\.net/movie/[^?]+\.jpg(?:\?[^?]+)?',
                'description': 'md5:a384a62937866101f86902f21752cd89',
                'upload_date': '20231017',
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
