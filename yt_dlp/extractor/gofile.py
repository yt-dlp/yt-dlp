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
    }]

    def _entries(self, file_id):

        # Create guest account
        accountdata = self._download_json('https://api.gofile.io/createAccount', 'Gofile', note='Getting a new guest account')
        accountToken = accountdata['data']['token']

        # Get file list
        requesturl = f'https://api.gofile.io/getContent?contentId={file_id}&token={accountToken}&websiteToken=websiteToken&cache=true'
        filelist = self._download_json(requesturl, 'Gofile', note='Getting filelist')
        status = filelist['status']
        if status != "ok":
            raise ExtractorError('Received error from service, status: %s\n' % status, expected=True)

        contents = try_get(filelist, lambda x: x['data']['contents'], dict)

        for _, file in contents.items():
            filedata = {
                'id': file['id'],
                'title': file['name'].rsplit('.', 1)[0],
                'url': file['directLink'],
                'filesize': file['size'],
                'release_timestamp': file['createTime']
            }
            yield filedata

        # Set guest accountToken cookie to allow downloads
        self._set_cookie('gofile.io', 'accountToken', accountToken)

    def _real_extract(self, url):
        file_id = self._match_id(url)

        # Start extraction on entries
        return self.playlist_result(self._entries(file_id), playlist_id=file_id)
