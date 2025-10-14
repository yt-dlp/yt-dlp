import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class AnimeOnegaiIE(InfoExtractor):
    _NETRC_MACHINE = 'animeonegai'
    _VALID_URL = r'https?://(?:www\.)?animeonegai\.com/(?P<language>[a-z]{2})/watch/(?P<id>\w+)'
    _GEO_COUNTRIES = ['MX']
    _TESTS = [{
        'url': 'https://www.animeonegai.com/es/watch/4Bpd6m6gGYVxdspKn?time=0&serie=true',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '4Bpd6m6gGYVxdspKn',
            'ext': 'mp4',
            'title': 'Ep. 1: Eikichi Onizuka, 22 años: ¡Comienza la legendaria práctica docente del ex delincuente!',
            'thumbnail': 'https://img-cdn.b-cdn.net/images/ayB0woggovEvoieXJ_1733001177.jpg',
            'description': 'Eikichi Onizuka, de 22 años, fue un reconocido miembro de una pandilla de motociclistas durante su época de preparatoria. Ahora, su sueño de convertirse en profesor se hace realidad al comenzar su práctica docente. Espera con entusiasmo vivir un romance prohibido con una estudiante, pero le asignan una clase de jóvenes problemáticos. Allí conoce a la hermosa Nanako Mizuki, quien lo invita a su habitación después de clases. Sin embargo, pronto descubre que todo parece ser una trampa...',
            'tags': ['Romance', 'Comedia', 'Drama', 'Serie'],
            'series': 'GTO',
            'episode_number': 1,
        },
        'skip': 'Login Required',
    }]
    _DEVICE_ID = str(uuid.uuid4())
    _HEADERS = {
        'Authorization': None,
        'Content-Type': 'application/json',
        'Host': 'api.animeonegai.com',
    }

    def _perform_login(self, username, password):
        if (username.lower() == 'token' and password is not None):
            self._HEADERS['Authorization'] = f'Bearer {password}'
            self.report_login()
        elif (username.lower() != 'token' and password is not None):
            raise ExtractorError('Login type not supported', expected=True)

    def _real_extract(self, url):
        if (self._HEADERS['Authorization'] is None):
            raise ExtractorError(
                'Use "--username token" and "--password <ott_token>" to log in. The ott_token can be found in Local Storage using the Developer Tools, after login in a browser window to Anime Onegai site', expected=True)

        language, video_id = self._match_valid_url(url).group('language', 'id')

        self._initialize_geo_bypass({
            'countries': self._GEO_COUNTRIES,
        })

        chapter_data = self._download_json(
            f'https://api.animeonegai.com/v1/restricted/chapter/entry/{video_id}',
            video_id, 'Downloading Chapter Data', headers=self._HEADERS, query={'lang': language})

        if (chapter_data.get('ID') == 0):
            raise ExtractorError('Chapter data not found', expected=True)

        asset_id = int_or_none(chapter_data.get('asset_id'))
        asset_data = self._download_json(
            f'https://api.animeonegai.com/v1/restricted/asset/public/{asset_id}',
            video_id, 'Downloading Asset Data', headers=self._HEADERS, query={'lang': language, 'cache': 'true'})

        video_entry = str_or_none(chapter_data.get('video_entry'))
        video_data = self._download_json(
            f'https://api.animeonegai.com/v1/media/{video_entry}',
            video_id, 'Downloading Video Data', headers=self._HEADERS,
            query={'tv': 'false', 'mobile': 'false', 'device_id': self._DEVICE_ID, 'platform': 'web'})

        if (video_data.get('drm') and not self.get_param('allow_unplayable_formats')):
            raise ExtractorError('The video is DRM protected', expected=True)

        formats = self._extract_mpd_formats(video_data['dash'], video_id)
        subtitles = {}

        for subtitle in video_data.get('subtitles') or []:
            subtitles.setdefault(str_or_none(subtitle.get('lang', language)), []).append({
                'url': url_or_none(subtitle.get('url')),
                'ext': determine_ext(str_or_none(subtitle.get('url'))),
                'name': str_or_none(subtitle.get('name')),
            })

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(chapter_data, {
                'title': ('name', {str}),
                'thumbnail': ('thumbnail', {url_or_none}),
                'description': ('description', {str}),
                'episode_number': ('number', {int_or_none}),
            }),
            **traverse_obj(asset_data, {
                'series': ('title', {str}),
                'tags': ('tags_list', ..., 'name', {str}),
            }),
        }
