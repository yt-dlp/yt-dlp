from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    int_or_none,
    js_to_json,
    remove_end,
    unified_strdate,
)


class VidbitIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vidbit\.co/(?:watch|embed)\?.*?\bv=(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        'url': 'http://www.vidbit.co/watch?v=jkL2yDOEq2',
        'md5': '1a34b7f14defe3b8fafca9796892924d',
        'info_dict': {
            'id': 'jkL2yDOEq2',
            'ext': 'mp4',
            'title': 'Intro to VidBit',
            'description': 'md5:5e0d6142eec00b766cbf114bfd3d16b7',
            'thumbnail': r're:https?://.*\.jpg$',
            'upload_date': '20160618',
            'view_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'http://www.vidbit.co/embed?v=jkL2yDOEq2&auto=0&water=0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            compat_urlparse.urljoin(url, '/watch?v=%s' % video_id), video_id)

        video_url, title = [None] * 2

        config = self._parse_json(self._search_regex(
            r'(?s)\.setup\(({.+?})\);', webpage, 'setup', default='{}'),
            video_id, transform_source=js_to_json)
        if config:
            if config.get('file'):
                video_url = compat_urlparse.urljoin(url, config['file'])
            title = config.get('title')

        if not video_url:
            video_url = compat_urlparse.urljoin(url, self._search_regex(
                r'file\s*:\s*(["\'])(?P<url>(?:(?!\1).)+)\1',
                webpage, 'video URL', group='url'))

        if not title:
            title = remove_end(
                self._html_search_regex(
                    (r'<h1>(.+?)</h1>', r'<title>(.+?)</title>'),
                    webpage, 'title', default=None) or self._og_search_title(webpage),
                ' - VidBit')

        description = self._html_search_meta(
            ('description', 'og:description', 'twitter:description'),
            webpage, 'description')

        upload_date = unified_strdate(self._html_search_meta(
            'datePublished', webpage, 'upload date'))

        view_count = int_or_none(self._search_regex(
            r'<strong>(\d+)</strong> views',
            webpage, 'view count', fatal=False))
        comment_count = int_or_none(self._search_regex(
            r'id=["\']cmt_num["\'][^>]*>\((\d+)\)',
            webpage, 'comment count', fatal=False))

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': self._og_search_thumbnail(webpage),
            'upload_date': upload_date,
            'view_count': view_count,
            'comment_count': comment_count,
        }
