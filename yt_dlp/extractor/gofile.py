import hashlib

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_get
)


class GofileIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gofile\.io/d/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://gofile.io/d/AMZyDw',
        'info_dict': {
            'id': 'AMZyDw',
        },
        'playlist_mincount': 2,
        'playlist': [{
            'info_dict': {
                'id': 'de571ac1-5edc-42e2-8ec2-bdac83ad4a31',
                'filesize': 928116,
                'ext': 'mp4',
                'title': 'nuuh',
                'release_timestamp': 1638338704,
                'release_date': '20211201',
            }
        }]
    }, {
        'url': 'https://gofile.io/d/is8lKr',
        'info_dict': {
            'id': 'TMjXd9',
            'ext': 'mp4',
        },
        'playlist_count': 0,
        'skip': 'No video/audio found at provided URL.',
    }, {
        'url': 'https://gofile.io/d/TMjXd9',
        'info_dict': {
            'id': 'TMjXd9',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://gofile.io/d/gqOtRf',
        'info_dict': {
            'id': 'gqOtRf',
        },
        'playlist_mincount': 1,
        'params': {
            'videopassword': 'password',
        },
    }]
    _TOKEN = None

    def _real_initialize(self):
        token = self._get_cookies('https://gofile.io/').get('accountToken')
        if token:
            self._TOKEN = token.value
            return

        account_data = self._download_json(
            'https://api.gofile.io/createAccount', None, note='Getting a new guest account')
        self._TOKEN = account_data['data']['token']
        self._set_cookie('.gofile.io', 'accountToken', self._TOKEN)

    def _entries(self, file_id):
        query_params = {
            'contentId': file_id,
            'token': self._TOKEN,
            'wt': '4fd6sg89d7s6',  # From https://gofile.io/dist/js/alljs.js
        }
        password = self.get_param('videopassword')
        if password:
            query_params['password'] = hashlib.sha256(password.encode('utf-8')).hexdigest()
        files = self._download_json(
            'https://api.gofile.io/getContent', file_id, note='Getting filelist', query=query_params)

        status = files['status']
        if status == 'error-passwordRequired':
            raise ExtractorError(
                'This video is protected by a password, use the --video-password option', expected=True)
        elif status != 'ok':
            raise ExtractorError(f'{self.IE_NAME} said: status {status}', expected=True)

        found_files = False
        for file in (try_get(files, lambda x: x['data']['contents'], dict) or {}).values():
            file_type, file_format = file.get('mimetype').split('/', 1)
            if file_type not in ('video', 'audio') and file_format != 'vnd.mts':
                continue

            found_files = True
            file_url = file.get('link')
            if file_url:
                yield {
                    'id': file['id'],
                    'title': file['name'].rsplit('.', 1)[0],
                    'url': file_url,
                    'filesize': file.get('size'),
                    'release_timestamp': file.get('createTime')
                }

        if not found_files:
            raise ExtractorError('No video/audio found at provided URL.', expected=True)

    def _real_extract(self, url):
        file_id = self._match_id(url)
        return self.playlist_result(self._entries(file_id), playlist_id=file_id)
