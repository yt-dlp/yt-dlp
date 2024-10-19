import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_element_by_attribute,
    int_or_none,
)


class SampleFocusIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?samplefocus\.com/samples/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://samplefocus.com/samples/lil-peep-sad-emo-guitar',
        'md5': '48c8d62d60be467293912e0e619a5120',
        'info_dict': {
            'id': '40316',
            'display_id': 'lil-peep-sad-emo-guitar',
            'ext': 'mp3',
            'title': 'Lil Peep Sad Emo Guitar',
            'thumbnail': r're:^https?://.+\.png',
            'license': 'Standard License',
            'uploader': 'CapsCtrl',
            'uploader_id': 'capsctrl',
            'like_count': int,
            'comment_count': int,
            'categories': ['Samples', 'Guitar', 'Electric guitar'],
        },
    }, {
        'url': 'https://samplefocus.com/samples/dababy-style-bass-808',
        'only_matching': True,
    }, {
        'url': 'https://samplefocus.com/samples/young-chop-kick',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id, impersonate=True)

        sample_id = self._search_regex(
            r'<input[^>]+id=(["\'])sample_id\1[^>]+value=(?:["\'])(?P<id>\d+)',
            webpage, 'sample id', group='id')

        title = self._og_search_title(webpage, fatal=False) or self._html_search_regex(
            r'<h1>(.+?)</h1>', webpage, 'title')

        mp3_url = self._search_regex(
            r'<input[^>]+id=(["\'])sample_mp3\1[^>]+value=(["\'])(?P<url>(?:(?!\2).)+)',
            webpage, 'mp3', fatal=False, group='url') or extract_attributes(self._search_regex(
                r'<meta[^>]+itemprop=(["\'])contentUrl\1[^>]*>',
                webpage, 'mp3 url', group=0))['content']

        thumbnail = self._og_search_thumbnail(webpage) or self._html_search_regex(
            r'<img[^>]+class=(?:["\'])waveform responsive-img[^>]+src=(["\'])(?P<url>(?:(?!\1).)+)',
            webpage, 'mp3', fatal=False, group='url')

        comments = []
        for author_id, author, body in re.findall(r'(?s)<p[^>]+class="comment-author"><a[^>]+href="/users/([^"]+)">([^"]+)</a>.+?<p[^>]+class="comment-body">([^>]+)</p>', webpage):
            comments.append({
                'author': author,
                'author_id': author_id,
                'text': body,
            })

        uploader_id = uploader = None
        mobj = re.search(r'>By <a[^>]+href="/users/([^"]+)"[^>]*>([^<]+)', webpage)
        if mobj:
            uploader_id, uploader = mobj.groups()

        breadcrumb = get_element_by_attribute('typeof', 'BreadcrumbList', webpage)
        categories = []
        if breadcrumb:
            for _, name in re.findall(r'<span[^>]+property=(["\'])name\1[^>]*>([^<]+)', breadcrumb):
                categories.append(name)

        def extract_count(klass):
            return int_or_none(self._html_search_regex(
                rf'<span[^>]+class=(?:["\'])?{klass}-count[^>]*>(\d+)',
                webpage, klass, fatal=False))

        return {
            'id': sample_id,
            'title': title,
            'formats': [{
                'url': mp3_url,
                'ext': 'mp3',
                'vcodec': 'none',
                'acodec': 'mp3',
                'http_headers': {
                    'Referer': url,
                },
            }],
            'display_id': display_id,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'license': self._html_search_regex(
                r'<a[^>]+href=(["\'])/license\1[^>]*>(?P<license>[^<]+)<',
                webpage, 'license', fatal=False, group='license'),
            'uploader_id': uploader_id,
            'like_count': extract_count(f'sample-{sample_id}-favorites'),
            'comment_count': extract_count('comments'),
            'comments': comments,
            'categories': categories,
        }
