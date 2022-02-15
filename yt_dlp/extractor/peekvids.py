# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import remove_end


class PeekVidsIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?peekvids\.com/
        (?:(?:[^/?#]+/){2}|embed/?\?(?:[^#]*&)?v=)
        (?P<id>[^/?&#]*)
    '''
    _TESTS = [{
        'url': 'https://peekvids.com/pc/dane-jones-cute-redhead-with-perfect-tits-with-mini-vamp/BSyLMbN0YCd',
        'md5': '2ff6a357a9717dc9dc9894b51307e9a2',
        'info_dict': {
            'id': 'BSyLMbN0YCd',
            'ext': 'mp4',
            'title': 'Dane Jones - Cute redhead with perfect tits with Mini Vamp',
            'age_limit': 18,
        },
    }]
    _DOMAIN = 'www.peekvids.com'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        short_video_id = self._html_search_regex(r'<video [^>]*data-id="(.+?)"', webpage, 'short video ID')
        srcs = self._download_json(
            f'https://{self._DOMAIN}/v-alt/{short_video_id}', video_id,
            note='Downloading list of source files')
        formats = [{
            'url': url,
            'ext': 'mp4',
            'format_id': name[8:],
        } for name, url in srcs.items() if len(name) > 8 and name.startswith('data-src')]
        if not formats:
            formats = [{'url': url} for url in srcs.values()]
        self._sort_formats(formats)

        title = remove_end(self._html_search_regex(
            (r'<h1.*?>\s*(.+?)\s*</h1>', r'<title>\s*(.+?)\s*</title>'),
            webpage, 'video title', default=None), ' - PeekVids')

        return {
            'id': video_id,
            'title': title,
            'age_limit': 18,
            'formats': formats,
        }


class PlayVidsIE(PeekVidsIE):
    _VALID_URL = r'https?://(?:www\.)?playvids\.com/(?:embed/|[^/]{2}/)?(?P<id>[^/?#]*)'
    _TESTS = [{
        'url': 'https://www.playvids.com/U3pBrYhsjXM/pc/dane-jones-cute-redhead-with-perfect-tits-with-mini-vamp',
        'md5': '2f12e50213dd65f142175da633c4564c',
        'info_dict': {
            'id': 'U3pBrYhsjXM',
            'ext': 'mp4',
            'title': 'Dane Jones - Cute redhead with perfect tits with Mini Vamp',
            'age_limit': 18,
        },
    }, {
        'url': 'https://www.playvids.com/es/U3pBrYhsjXM/pc/dane-jones-cute-redhead-with-perfect-tits-with-mini-vamp',
        'md5': '2f12e50213dd65f142175da633c4564c',
        'info_dict': {
            'id': 'U3pBrYhsjXM',
            'ext': 'mp4',
            'title': 'Dane Jones - Cute redhead with perfect tits with Mini Vamp',
            'age_limit': 18,
        },
    }, {
        'url': 'https://www.playvids.com/embed/U3pBrYhsjXM',
        'md5': '2f12e50213dd65f142175da633c4564c',
        'info_dict': {
            'id': 'U3pBrYhsjXM',
            'ext': 'mp4',
            'title': 'U3pBrYhsjXM',
            'age_limit': 18,
        },
    }]
    _DOMAIN = 'www.playvids.com'
