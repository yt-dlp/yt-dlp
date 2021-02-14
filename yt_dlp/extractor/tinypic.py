from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import ExtractorError


class TinyPicIE(InfoExtractor):
    IE_NAME = 'tinypic'
    IE_DESC = 'tinypic.com videos'
    _VALID_URL = r'https?://(?:.+?\.)?tinypic\.com/player\.php\?v=(?P<id>[^&]+)&s=\d+'

    _TESTS = [
        {
            'url': 'http://tinypic.com/player.php?v=6xw7tc%3E&s=5#.UtqZmbRFCM8',
            'md5': '609b74432465364e72727ebc6203f044',
            'info_dict': {
                'id': '6xw7tc',
                'ext': 'flv',
                'title': 'shadow phenomenon weird',
            },
        },
        {
            'url': 'http://de.tinypic.com/player.php?v=dy90yh&s=8',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id, 'Downloading page')

        mobj = re.search(r'(?m)fo\.addVariable\("file",\s"(?P<fileid>[\da-z]+)"\);\n'
                         r'\s+fo\.addVariable\("s",\s"(?P<serverid>\d+)"\);', webpage)
        if mobj is None:
            raise ExtractorError('Video %s does not exist' % video_id, expected=True)

        file_id = mobj.group('fileid')
        server_id = mobj.group('serverid')

        KEYWORDS_SUFFIX = ', Video, images, photos, videos, myspace, ebay, video hosting, photo hosting'
        keywords = self._html_search_meta('keywords', webpage, 'title')
        title = keywords[:-len(KEYWORDS_SUFFIX)] if keywords.endswith(KEYWORDS_SUFFIX) else ''

        video_url = 'http://v%s.tinypic.com/%s.flv' % (server_id, file_id)
        thumbnail = 'http://v%s.tinypic.com/%s_th.jpg' % (server_id, file_id)

        return {
            'id': file_id,
            'url': video_url,
            'thumbnail': thumbnail,
            'title': title
        }
