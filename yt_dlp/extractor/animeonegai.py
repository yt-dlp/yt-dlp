import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    url_or_none,
)
from ..utils.traversal import subs_list_to_dict, traverse_obj


class AnimeOnegaiIE(InfoExtractor):
    _NETRC_MACHINE = 'animeonegai'
    _VALID_URL = r'https?://(?:www\.)?animeonegai\.com/(?P<language>[a-z]{2})/watch/(?P<id>\w+)'
    _GEO_COUNTRIES = ['MX']
    _TESTS = [{
        'url': 'https://www.animeonegai.com/es/watch/4Bpd6m6gGYVxdspKn?time=0&serie=true',
        'md5': '14267b6a820872df1f7eef973c44e70f',
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
    }]
    _LOGIN_HINT = ('Use --username token --password ACCESS_TOKEN where ACCESS_TOKEN '
                   'is the "ott_token" from your browser local storage')
    _DEVICE_ID = str(uuid.uuid4())
    _HEADERS = {
        'Authorization': None,
        'Content-Type': 'application/json',
    }

    def _perform_login(self, username, password):
        if self._HEADERS['Authorization']:
            return

        if username != 'token':
            self.raise_login_required(f'Only token-based login is supported. {self._LOGIN_HINT}', method=None)

        self._HEADERS['Authorization'] = f'Bearer {password}'

    def _real_initialize(self):
        if not self._HEADERS['Authorization']:
            self.raise_login_required(f'Login required. {self._LOGIN_HINT}', method=None)

    def _real_extract(self, url):
        language, video_id = self._match_valid_url(url).group('language', 'id')

        chapter_data = self._download_json(
            f'https://api.animeonegai.com/v1/restricted/chapter/entry/{video_id}',
            video_id, 'Downloading Chapter Data', headers=self._HEADERS, query={'lang': language})

        if (chapter_data.get('ID') == 0):
            raise ExtractorError('Chapter data not found', expected=True)

        asset_data = self._download_json(
            f'https://api.animeonegai.com/v1/restricted/asset/public/{chapter_data["asset_id"]}',
            video_id, 'Downloading Asset Data', headers=self._HEADERS, query={'lang': language, 'cache': 'true'})

        video_data = self._download_json(
            f'https://api.animeonegai.com/v1/media/{chapter_data["video_entry"]}',
            video_id, 'Downloading Video Data', headers=self._HEADERS,
            query={'tv': 'false', 'mobile': 'false', 'device_id': self._DEVICE_ID, 'platform': 'web'})

        if (video_data.get('drm') and not self.get_param('allow_unplayable_formats')):
            self.report_drm(video_id)

        formats = self._extract_mpd_formats(video_data['dash'], video_id)
        subtitles = traverse_obj(video_data, ('subtitles', ..., {
            'id': ('lang', {str}),
            'url': ('url', {url_or_none}),
            'name': ('name', {str}),
        }, all, {subs_list_to_dict(lang=language)}))

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
