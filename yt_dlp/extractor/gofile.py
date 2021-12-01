# coding: utf-8
from .common import InfoExtractor
from ..utils import (
    ExtractorError
)


class GofileIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gofile\.io/d/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://gofile.io/d/AMZyDw',
        'md5': '57c04f65556ddbecf9697528274c3212',
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
        status = accountdata[0]['status']
        accountToken = accountdata[0]['data']['token']
        print("[Gofile] Status:", status, "accountToken:", accountToken)

        # Get file list
        requesturl = f"https://api.gofile.io/getContent?contentId={file_id}&token={accountToken}&websiteToken=websiteToken&cache=true"
        filelist = self._download_json_handle(requesturl, 'Gofile', note='Getting filelist')

        # Create all entries
        def entries():
            contents = filelist[0]['data']['contents']
            key_list = [key for key in contents]

            for key in key_list:
                try:
                    file = contents[key]
                    filedata = {
                        'id': file_id,
                        'title': file['name'],
                        'url': file['directLink'],
                        'filesize': file['size'],
                        'release_timestamp': file['createTime']
                    }
                    yield filedata
                except ExtractorError as e:
                    print(e)

        # Set accountToken to allow downloads
        self._set_cookie('gofile.io', 'accountToken', accountToken)

        # Start extraction on entries
        return self.playlist_result(entries())
