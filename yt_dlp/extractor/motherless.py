import datetime
import re

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    ExtractorError,
    InAdvancePagedList,
    str_to_int,
    unified_strdate,
)


class MotherlessIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?motherless\.com/(?:g/[a-z0-9_]+/)?(?P<id>[A-F0-9]+)'
    _TESTS = [{
        'url': 'http://motherless.com/AC3FFE1',
        'md5': '310f62e325a9fafe64f68c0bccb6e75f',
        'info_dict': {
            'id': 'AC3FFE1',
            'ext': 'mp4',
            'title': 'Fucked in the ass while playing PS3',
            'categories': ['Gaming', 'anal', 'reluctant', 'rough', 'Wife'],
            'upload_date': '20100913',
            'uploader_id': 'famouslyfuckedup',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
        }
    }, {
        'url': 'http://motherless.com/532291B',
        'md5': 'bc59a6b47d1f958e61fbd38a4d31b131',
        'info_dict': {
            'id': '532291B',
            'ext': 'mp4',
            'title': 'Amazing girl playing the omegle game, PERFECT!',
            'categories': ['Amateur', 'webcam', 'omegle', 'pink', 'young', 'masturbate', 'teen',
                           'game', 'hairy'],
            'upload_date': '20140622',
            'uploader_id': 'Sulivana7x',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
        },
        'skip': '404',
    }, {
        'url': 'http://motherless.com/g/cosplay/633979F',
        'md5': '0b2a43f447a49c3e649c93ad1fafa4a0',
        'info_dict': {
            'id': '633979F',
            'ext': 'mp4',
            'title': 'Turtlette',
            'categories': ['superheroine heroine  superher'],
            'upload_date': '20140827',
            'uploader_id': 'shade0230',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
        }
    }, {
        # no keywords
        'url': 'http://motherless.com/8B4BBC1',
        'only_matching': True,
    }, {
        # see https://motherless.com/videos/recent for recent videos with
        # uploaded date in "ago" format
        'url': 'https://motherless.com/3C3E2CF',
        'info_dict': {
            'id': '3C3E2CF',
            'ext': 'mp4',
            'title': 'a/ Hot Teens',
            'categories': list,
            'upload_date': '20210104',
            'uploader_id': 'yonbiw',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if any(p in webpage for p in (
                '<title>404 - MOTHERLESS.COM<',
                ">The page you're looking for cannot be found.<")):
            raise ExtractorError('Video %s does not exist' % video_id, expected=True)

        if '>The content you are trying to view is for friends only.' in webpage:
            raise ExtractorError('Video %s is for friends only' % video_id, expected=True)

        title = self._html_search_regex(
            (r'(?s)<div[^>]+\bclass=["\']media-meta-title[^>]+>(.+?)</div>',
             r'id="view-upload-title">\s+([^<]+)<'), webpage, 'title')
        video_url = (self._html_search_regex(
            (r'setup\(\{\s*["\']file["\']\s*:\s*(["\'])(?P<url>(?:(?!\1).)+)\1',
             r'fileurl\s*=\s*(["\'])(?P<url>(?:(?!\1).)+)\1'),
            webpage, 'video URL', default=None, group='url')
            or 'http://cdn4.videos.motherlessmedia.com/videos/%s.mp4?fs=opencloud' % video_id)
        age_limit = self._rta_search(webpage)
        view_count = str_to_int(self._html_search_regex(
            (r'>([\d,.]+)\s+Views<', r'<strong>Views</strong>\s+([^<]+)<'),
            webpage, 'view count', fatal=False))
        like_count = str_to_int(self._html_search_regex(
            (r'>([\d,.]+)\s+Favorites<',
             r'<strong>Favorited</strong>\s+([^<]+)<'),
            webpage, 'like count', fatal=False))

        upload_date = unified_strdate(self._search_regex(
            r'class=["\']count[^>]+>(\d+\s+[a-zA-Z]{3}\s+\d{4})<', webpage,
            'upload date', default=None))
        if not upload_date:
            uploaded_ago = self._search_regex(
                r'>\s*(\d+[hd])\s+[aA]go\b', webpage, 'uploaded ago',
                default=None)
            if uploaded_ago:
                delta = int(uploaded_ago[:-1])
                _AGO_UNITS = {
                    'h': 'hours',
                    'd': 'days',
                }
                kwargs = {_AGO_UNITS.get(uploaded_ago[-1]): delta}
                upload_date = (datetime.datetime.utcnow() - datetime.timedelta(**kwargs)).strftime('%Y%m%d')

        comment_count = webpage.count('class="media-comment-contents"')
        uploader_id = self._html_search_regex(
            (r'"media-meta-member">\s+<a href="/m/([^"]+)"',
             r'<span\b[^>]+\bclass="username">([^<]+)</span>'),
            webpage, 'uploader_id', fatal=False)
        categories = self._html_search_meta('keywords', webpage, default=None)
        if categories:
            categories = [cat.strip() for cat in categories.split(',')]

        return {
            'id': video_id,
            'title': title,
            'upload_date': upload_date,
            'uploader_id': uploader_id,
            'thumbnail': self._og_search_thumbnail(webpage),
            'categories': categories,
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'age_limit': age_limit,
            'url': video_url,
        }


class MotherlessPaginatedIE(InfoExtractor):
    _PAGE_SIZE = 60

    def _extract_entries(self, webpage, base):
        for mobj in re.finditer(r'href=".*(?P<href>\/[A-F0-9]+)"\s+title="(?P<title>[^"]+)', webpage):
            video_url = compat_urlparse.urljoin(base, mobj.group("href"))
            video_id = MotherlessIE.get_temp_id(video_url)

            if video_id:
                yield self.url_result(
                    video_url, ie=MotherlessIE.ie_key(), video_id=video_id,
                    video_title=mobj.group('title'))

    def _real_extract(self, url):
        _id = self._match_id(url)
        webpage = self._download_webpage(url, _id)
        title = self._search_regex(r'^([\w\s]+)\s+', self._html_extract_title(webpage), 'title')
        page_count = self._int(self._search_regex(
            r'(\d+)</a><a[^>]+rel="next"',
            webpage, 'page_count', default=1), 'page_count')

        def _get_page(idx):
            webpage = self._download_webpage(
                url, _id, query={'page': idx},
                note=f'Downloading page {idx}/{page_count}')

            yield from self._extract_entries(webpage, url)

        return self.playlist_result(
            InAdvancePagedList(_get_page, page_count, MotherlessPaginatedIE._PAGE_SIZE), _id, title)


class MotherlessGroupIE(MotherlessPaginatedIE):
    _VALID_URL = r'https?://(?:www\.)?motherless\.com/gv/(?P<id>[a-z0-9_]+)'
    _TESTS = [{
        'url': 'http://motherless.com/gv/movie_scenes',
        'info_dict': {
            'id': 'movie_scenes',
            'title': 'Movie Scenes',
        },
        'playlist_mincount': 8 * MotherlessPaginatedIE._PAGE_SIZE + 1,
    }, {
        'url': 'http://motherless.com/gv/sex_must_be_funny',
        'info_dict': {
            'id': 'sex_must_be_funny',
            'title': 'Sex must be funny',
        },
        'playlist_mincount': 0,
        'expected_warnings': [
            'This group has no videos.',
        ]
    }, {
        'url': 'https://motherless.com/gv/beautiful_cock',
        'info_dict': {
            'id': 'beautiful_cock',
            'title': 'Beautiful Cock',
        },
        'playlist_mincount': 33 * MotherlessPaginatedIE._PAGE_SIZE + 1,
    }]


class MotherlessGalleryIE(MotherlessPaginatedIE):
    _VALID_URL = r'https?://(?:www\.)?motherless\.com/GV(?P<id>[A-F0-9]+)'
    _TESTS = [{
        'url': 'https://motherless.com/GV338999F',
        'info_dict': {
            'id': '338999F',
            'title': 'Random',
        },
        'playlist_mincount': 3 * MotherlessPaginatedIE._PAGE_SIZE + 1,
    }, {
        'url': 'https://motherless.com/GVABD6213',
        'info_dict': {
            'id': 'ABD6213',
            'title': 'Cuties',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://motherless.com/GVBCF7622',
        'info_dict': {
            'id': 'BCF7622',
            'title': 'Vintage',
        },
        'playlist_mincount': 0,
    }]
