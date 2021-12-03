# coding: utf-8
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
                'title': 'nuuh'
            }
        }]
    }, {  # URL to test mixed file types
        'url': 'https://gofile.io/d/avt34h',
        'info_dict': {
            'id': 'avt34h',
        },
        'playlist_mincount': 1,
    }, {  # URL to test no video/audio error
        'url': 'https://gofile.io/d/aB03lZ',
        'info_dict': {
            'id': 'aB03lZ',
        },
        'playlist_count': 0,
        'skip': 'No video/audio found at provided URL.',
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
        self._set_cookie('gofile.io', 'accountToken', self._TOKEN)

    def _entries(self, file_id):
        files = self._download_json(
            f'https://api.gofile.io/getContent?contentId={file_id}&token={self._TOKEN}&websiteToken=websiteToken&cache=true',
            'Gofile', note='Getting filelist')

        status = files['status']
        if status != 'ok':
            raise ExtractorError(f'{self.IE_NAME} said: status {status}', expected=True)

        found_files = False
        for file in (try_get(files, lambda x: x['data']['contents'], dict) or {}).values():
            file_type, file_format = file.get('mimetype').split('/', 1)
            if file_type not in ('video', 'audio') and file_format != 'vnd.mts':
                continue

            found_files = True
            file_url = file.get('directLink')
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
