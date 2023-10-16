import os.path

from .common import InfoExtractor


class SaveFromIE(InfoExtractor):
    IE_NAME = 'savefrom.net'
    _VALID_URL = r'https?://[^.]+\.savefrom\.net/\#url=(?P<url>.*)$'

    _TEST = {
        'url': 'http://en.savefrom.net/#url=http://youtube.com/watch?v=UlVRAPW2WJY&utm_source=youtube.com&utm_medium=short_domains&utm_campaign=ssyoutube.com',
        'info_dict': {
            'id': 'UlVRAPW2WJY',
            'ext': 'mp4',
            'title': 'About Team Radical MMA | MMA Fighting',
            'upload_date': '20120816',
            'uploader': 'Howcast',
            'uploader_id': 'Howcast',
            'description': r're:(?s).* Hi, my name is Rene Dreifuss\. And I\'m here to show you some MMA.*',
        },
        'params': {
            'skip_download': True
        }
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = os.path.splitext(url.split('/')[-1])[0]

        return self.url_result(mobj.group('url'), video_id=video_id)
