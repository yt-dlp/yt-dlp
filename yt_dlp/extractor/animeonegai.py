import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    str_or_none,
    url_or_none,
)


class AnimeOnegaiIE(InfoExtractor):
    _NETRC_MACHINE = 'animeonegai'
    _VALID_URL = r'https?://(?:www\.)?animeonegai\.com/(?P<language>[a-z]{2})/watch/(?P<id>[a-zA-Z0-9]+)(?:\?|&)(\w+)=([^&]*)'
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
            raise ExtractorError('Use "--username token" and ""--password <auth_token>"" to log in', expected=True)

        language, video_id = self._match_valid_url(url).group('language', 'id')

        if (language is None):
            language = 'es'

        if (video_id is None):
            raise ExtractorError('Video id not provided', expected=True)

        chapter_json = self._download_json(f'https://api.animeonegai.com/v1/restricted/chapter/entry/{video_id}?lang={language}', video_id, 'Downloading Chapter Data', headers=self._HEADERS)

        if (chapter_json is None or chapter_json.get('ID') == 0):
            raise ExtractorError('Chapter data not found', expected=True)

        asset_id = int_or_none(chapter_json.get('asset_id'))
        asset_json = self._download_json(f'https://api.animeonegai.com/v1/restricted/asset/public/{asset_id}?lang={language}&cache=true', video_id, 'Downloading Asset Data', headers=self._HEADERS)

        video_entry = str_or_none(chapter_json.get('video_entry'))
        video_json = self._download_json(f'https://api.animeonegai.com/v1/media/{video_entry}?tv=false&mobile=false&device_id={self._DEVICE_ID}&platform=web', video_id, 'Downloading Video Data', headers=self._HEADERS)

        if (video_json is None or video_json.get('ID') == 0):
            raise ExtractorError('Video data not found', expected=True)

        formats = self._extract_mpd_formats(url_or_none(video_json.get('dash')), video_id, mpd_id='dash', fatal=False)
        subtitles = {}
        tags = []

        for subtitle in video_json.get('subtitles') or []:
            subtitles.setdefault(str_or_none(subtitle.get('lang', language)), []).append({
                'url': url_or_none(subtitle.get('url')),
                'ext': determine_ext(str_or_none(subtitle.get('url'))),
                'name': str_or_none(subtitle.get('name')),
            })

        for tag in asset_json.get('tags_list') or []:
            tags.append(str_or_none(tag.get('name')))

        return {
            'id': video_id,
            'title': str_or_none(chapter_json.get('name')),
            'formats': formats,
            'thumbnail': str_or_none(chapter_json.get('thumbnail')),
            'description': str_or_none(chapter_json.get('description')),
            'subtitles': subtitles,
            'tags': tags,
            'series': str_or_none(asset_json.get('title')),
            'episode_number': int_or_none(chapter_json.get('number')),
        }
