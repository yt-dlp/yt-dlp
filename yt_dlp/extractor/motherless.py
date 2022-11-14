import datetime
import re

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    ExtractorError,
    InAdvancePagedList,
    orderedSet,
    str_to_int,
    unified_strdate,
)


class MotherlessIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?motherless\.com/(?:g/[a-z0-9_]+/)?(?P<id>[A-Z0-9]+)'
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
            'uploader_id': 'anonymous',
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

        comment_count = len(re.findall(r'''class\s*=\s*['"]media-comment-contents\b''', webpage))
        uploader_id = self._html_search_regex(
            (r'''<span\b[^>]+\bclass\s*=\s*["']username\b[^>]*>([^<]+)</span>''',
             r'''(?s)['"](?:media-meta-member|thumb-member-username)\b[^>]+>\s*<a\b[^>]+\bhref\s*=\s*['"]/m/([^"']+)'''),
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


class MotherlessGroupIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?motherless\.com/gv?/(?P<id>[a-z0-9_]+)'
    _TESTS = [{
        'url': 'http://motherless.com/g/movie_scenes',
        'info_dict': {
            'id': 'movie_scenes',
            'title': 'Movie Scenes',
            'description': 'Hot and sexy scenes from "regular" movies... '
                           'Beautiful actresses fully nude... A looot of '
                           'skin! :)Enjoy!',
        },
        'playlist_mincount': 662,
    }, {
        'url': 'http://motherless.com/gv/sex_must_be_funny',
        'info_dict': {
            'id': 'sex_must_be_funny',
            'title': 'Sex must be funny',
            'description': 'Sex can be funny. Wide smiles,laugh, games, fun of '
                           'any kind!'
        },
        'playlist_mincount': 0,
        'expected_warnings': [
            'This group has no videos.',
        ]
    }, {
        'url': 'https://motherless.com/g/beautiful_cock',
        'info_dict': {
            'id': 'beautiful_cock',
            'title': 'Beautiful Cock',
            'description': 'Group for lovely cocks yours, mine, a friends anything human',
        },
        'playlist_mincount': 2500,
    }]

    @classmethod
    def suitable(cls, url):
        return (False if MotherlessIE.suitable(url)
                else super(MotherlessGroupIE, cls).suitable(url))

    def _extract_entries(self, webpage, base):
        entries = []
        for mobj in re.finditer(
                r'href="(?P<href>/[^"]+)"[^>]*>(?:\s*<img[^>]+alt="[^-]+-\s(?P<title>[^"]+)")?',
                webpage):
            video_url = compat_urlparse.urljoin(base, mobj.group('href'))
            if not MotherlessIE.suitable(video_url):
                continue
            video_id = MotherlessIE._match_id(video_url)
            title = mobj.group('title')
            entries.append(self.url_result(
                video_url, ie=MotherlessIE.ie_key(), video_id=video_id,
                video_title=title))
        # Alternative fallback
        if not entries:
            entries = [
                self.url_result(
                    compat_urlparse.urljoin(base, '/' + entry_id),
                    ie=MotherlessIE.ie_key(), video_id=entry_id)
                for entry_id in orderedSet(re.findall(
                    r'data-codename=["\']([A-Z0-9]+)', webpage))]
        return entries

    def _real_extract(self, url):
        group_id = self._match_id(url)
        page_url = compat_urlparse.urljoin(url, '/gv/%s' % group_id)
        webpage = self._download_webpage(page_url, group_id)
        title = self._search_regex(
            r'<title>([\w\s]+\w)\s+-', webpage, 'title', fatal=False)
        description = self._html_search_meta(
            'description', webpage, fatal=False)
        page_count = str_to_int(self._search_regex(
            r'(\d+)\s*</(?:a|span)>\s*<(?:a|span)[^>]+(?:>\s*NEXT|\brel\s*=\s*["\']?next)\b',
            webpage, 'page_count', default=0))
        if not page_count:
            message = self._search_regex(
                r'''class\s*=\s*['"]error-page\b[^>]*>\s*<p[^>]*>\s*(?P<error_msg>[^<]+)(?<=\S)\s*''',
                webpage, 'error_msg', default=None) or 'This group has no videos.'
            self.report_warning(message, group_id)
            page_count = 1
        PAGE_SIZE = 80

        def _get_page(idx):
            if idx > 0:
                webpage = self._download_webpage(
                    page_url, group_id, query={'page': idx + 1},
                    note='Downloading page %d/%d' % (idx + 1, page_count)
                )
            for entry in self._extract_entries(webpage, url):
                yield entry

        playlist = InAdvancePagedList(_get_page, page_count, PAGE_SIZE)

        return {
            '_type': 'playlist',
            'id': group_id,
            'title': title,
            'description': description,
            'entries': playlist
        }
