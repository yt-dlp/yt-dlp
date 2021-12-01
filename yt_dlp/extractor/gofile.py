# coding: utf-8
from .common import InfoExtractor
from ..utils import (
    ExtractorError
)


class GofileIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gofile\.io/d/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://gofile.io/d/AMZyDw',
        'md5': '774879ad31bc62c23269da8bf490d025',
        'info_dict': {
            'id': 'de571ac1-5edc-42e2-8ec2-bdac83ad4a31',
            'filesize': 928116,
            'ext': 'mp4',
            'title': 'nuuh.mp4'
        }
    }]

    def _real_extract(self, url):
        file_id = self._match_id(url)

        # Create guest account
        accountdata = self._download_json_handle('https://api.gofile.io/createAccount', 'Gofile', note='Getting a new guest account')
        accountToken = accountdata[0]['data']['token']

        # Get file list
        requesturl = f'https://api.gofile.io/getContent?contentId={file_id}&token={accountToken}&websiteToken=websiteToken&cache=true'
        filelist, _ = self._download_json_handle(requesturl, 'Gofile', note='Getting filelist')

        status = filelist['status']
        if status != "ok":
            raise ExtractorError('Received error from service, status: %s\n' % status, expected=True)

        # Create all entries
        def entries():
            contents = filelist['data']['contents']

            for _, file in contents.items():
                try:
                    filedata = {
                        'id': file['id'],
                        'title': file['name'],
                        'url': file['directLink'],
                        'filesize': file['size'],
                        'release_timestamp': file['createTime']
                    }
                    yield filedata
                except ExtractorError as e:
                    raise ExtractorError(e)

        # Set accountToken to allow downloads
        self._set_cookie('gofile.io', 'accountToken', accountToken)

        # Start extraction on entries
        return self.playlist_result(entries(), file_id)
