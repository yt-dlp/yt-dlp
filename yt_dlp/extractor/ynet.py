import json
import re
import urllib.parse

from .common import InfoExtractor


class YnetIE(InfoExtractor):
    _VALID_URL = r'https?://(?:.+?\.)?ynet\.co\.il/(?:.+?/)?0,7340,(?P<id>L(?:-[0-9]+)+),00\.html'
    _TESTS = [
        {
            'url': 'http://hot.ynet.co.il/home/0,7340,L-11659-99244,00.html',
            'info_dict': {
                'id': 'L-11659-99244',
                'ext': 'flv',
                'title': 'איש לא יודע מאיפה באנו',
                'thumbnail': r're:^https?://.*\.jpg',
            }
        }, {
            'url': 'http://hot.ynet.co.il/home/0,7340,L-8859-84418,00.html',
            'info_dict': {
                'id': 'L-8859-84418',
                'ext': 'flv',
                'title': "צפו: הנשיקה הלוהטת של תורגי' ויוליה פלוטקין",
                'thumbnail': r're:^https?://.*\.jpg',
            }
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        content = urllib.parse.unquote_plus(self._og_search_video_url(webpage))
        config = json.loads(self._search_regex(r'config=({.+?})$', content, 'video config'))
        f4m_url = config['clip']['url']
        title = self._og_search_title(webpage)
        m = re.search(r'ynet - HOT -- (["\']+)(?P<title>.+?)\1', title)
        if m:
            title = m.group('title')
        formats = self._extract_f4m_formats(f4m_url, video_id)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': self._og_search_thumbnail(webpage),
        }
