import json

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import ExtractorError
from ..utils.traversal import traverse_obj


class LaXarxaMesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?laxarxames\.cat/(?:[^/?#]+/)*?(player|movie-details)/(?P<id>\d+)'
    _NETRC_MACHINE = 'laxarxames'
    _TOKEN = None
    _TESTS = [{
        'url': 'https://www.laxarxames.cat/player/3459421',
        'md5': '0966f46c34275934c19af78f3df6e2bc',
        'info_dict': {
            'id': '6339612436112',
            'ext': 'mp4',
            'title': 'Resum | UA Horta — UD Viladecans',
            'timestamp': 1697905186,
            'thumbnail': r're:https?://.*\.jpg',
            'description': '',
            'upload_date': '20231021',
            'duration': 129.44,
            'tags': ['ott', 'esports', '23-24', ' futbol', ' futbol-partits', 'elit', 'resum'],
            'uploader_id': '5779379807001',
        },
        'skip': 'Requires login',
    }]

    def _perform_login(self, username, password):
        if self._TOKEN:
            return

        login = self._download_json(
            'https://api.laxarxames.cat/Authorization/SignIn', None, note='Logging in', headers={
                'X-Tenantorigin': 'https://laxarxames.cat',
                'Content-Type': 'application/json',
            }, data=json.dumps({
                'Username': username,
                'Password': password,
                'Device': {
                    'PlatformCode': 'WEB',
                    'Name': 'Mac OS ()',
                },
            }).encode(), expected_status=401)

        self._TOKEN = traverse_obj(login, ('AuthorizationToken', 'Token', {str}))
        if not self._TOKEN:
            raise ExtractorError('Login failed', expected=True)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        if not self._TOKEN:
            self.raise_login_required()

        media_play_info = self._download_json(
            'https://api.laxarxames.cat/Media/GetMediaPlayInfo', video_id,
            data=json.dumps({
                'MediaId': int(video_id),
                'StreamType': 'MAIN'
            }).encode(), headers={
                'Authorization': f'Bearer {self._TOKEN}',
                'X-Tenantorigin': 'https://laxarxames.cat',
                'Content-Type': 'application/json',
            })

        if not traverse_obj(media_play_info, ('ContentUrl', {str})):
            self.raise_no_formats('No video found', expected=True)

        return self.url_result(
            f'https://players.brightcove.net/5779379807001/default_default/index.html?videoId={media_play_info["ContentUrl"]}',
            BrightcoveNewIE, video_id, media_play_info.get('Title'))
