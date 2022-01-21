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

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        short_video_id = self._html_search_regex(r'<video [^>]*data-id="(.+?)"',
                                                 webpage, 'short video ID')
        srcs = self._download_json(
            f'https://www.peekvids.com/v-alt/{short_video_id}', video_id,
            note='Downloading list of source files')

        formats = [{
            'url': url,
            'ext': 'mp4',
            'format_id': name[8:],
        } for name, url in srcs.items() if len(name) > 8 and name.startswith('data-src')]
        self._sort_formats(formats)
        if not formats:
            formats = [{'url': url} for url in srcs.values()]

        title = self._html_search_regex(
            r'<h1\s+class="title-video"\s*>\s*(.+?)\s*</h1>', webpage,
            'video title', default=None)
        if title is None:
            title = self._html_search_regex(r'<title>\s*(.+?)\s*</title>',
                                            webpage, 'video title',
                                            default=video_id)
            title = remove_end(title, ' - PeekVids')

        return {
            'id': video_id,
            'title': title,
            'age_limit': 18,
            'formats': formats,
        }
