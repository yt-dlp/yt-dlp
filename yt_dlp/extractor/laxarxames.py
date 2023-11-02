import json

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor


class LaXarxaMesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?laxarxames\.cat/(?:[^/]+/)*?(player|movie-details)/(?P<id>[0-9]+)'
    _NETRC_MACHINE = 'laxarxames'
    _TOKEN = None
    _LOGIN_URL = 'https://www.laxarxames.cat/login'
    _TESTS = [{
        'url': 'https://www.laxarxames.cat/player/3459421',
        'md5': '0966f46c34275934c19af78f3df6e2bc',
        'info_dict': {
            'id': '3459421',
            'ext': 'mp4',
            'title': 'Resum | UA Horta — UD Viladecans',
            'type': 'video/mp4',
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
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://www.laxarxames.cat',
            }, data=json.dumps({
                'Username': username,
                'Password': password,
                'Device': {
                    'PlatformCode': 'WEB',
                    'Name': 'Mac OS ()',
                },
            }).encode('utf-8')
        )

        if not login['AuthorizationToken']:
            raise Exception('Login failed')
        else:
            self._TOKEN = login['AuthorizationToken']['Token']

    def _real_extract(self, url):
        video_id = self._match_id(url)

        if not self._TOKEN:
            self.raise_login_required()
        mediaplayinfo = self._download_json(
            'https://api.laxarxames.cat/Media/GetMediaPlayInfo',
            video_id,
            data=json.dumps({
                'MediaId': int(video_id),
                'StreamType': 'MAIN'
            }).encode('utf-8'),
            headers={
                'Authorization': 'Bearer ' + self._TOKEN,
                'X-Tenantorigin': 'https://laxarxames.cat',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://www.laxarxames.cat',
            }
        )

        content_url = mediaplayinfo['ContentUrl']
        video_title = mediaplayinfo['Title']

        return self.url_result(
            f'http://players.brightcove.net/5779379807001/default_default/index.html?videoId={content_url}',
            BrightcoveNewIE, video_id, video_title)
