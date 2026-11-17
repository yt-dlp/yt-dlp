import itertools
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    get_element_by_class,
    int_or_none,
    url_or_none,
    urljoin,
)


class ThisVidIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?thisvid\.com/(?P<type>videos|embed)/(?P<id>[A-Za-z0-9-]+)'
    _TESTS = [{
        'url': 'https://thisvid.com/videos/sitting-on-ball-tight-jeans/',
        'md5': '839becb572995687e11a69dc4358a386',
        'info_dict': {
            'id': '3533241',
            'ext': 'mp4',
            'title': 'Sitting on ball tight jeans',
            'description': 'md5:372353bb995883d1b65fddf507489acd',
            'thumbnail': r're:https?://\w+\.thisvid\.com/(?:[^/]+/)+3533241/preview\.jpg',
            'uploader_id': '150629',
            'uploader': 'jeanslevisjeans',
            'display_id': 'sitting-on-ball-tight-jeans',
            'age_limit': 18,
        },
    }, {
        'url': 'https://thisvid.com/embed/3533241/',
        'md5': '839becb572995687e11a69dc4358a386',
        'info_dict': {
            'id': '3533241',
            'ext': 'mp4',
            'title': 'Sitting on ball tight jeans',
            'thumbnail': r're:https?://\w+\.thisvid\.com/(?:[^/]+/)+3533241/preview\.jpg',
            'uploader_id': '150629',
            'uploader': 'jeanslevisjeans',
            'display_id': 'sitting-on-ball-tight-jeans',
            'age_limit': 18,
        },
    }]

    def _real_extract(self, url):
        main_id, type_ = re.match(self._VALID_URL, url).group('id', 'type')
        webpage = self._download_webpage(url, main_id)

        title = self._html_search_regex(
            r'<title\b[^>]*?>(?:Video:\s+)?(.+?)(?:\s+-\s+ThisVid(?:\.com| tube))?</title>',
            webpage, 'title')

        if type_ == 'embed':
            # look for more metadata
            video_alt_url = url_or_none(self._search_regex(
                rf'''video_alt_url\s*:\s+'({self._VALID_URL}/)',''',
                webpage, 'video_alt_url', default=None))
            if video_alt_url and video_alt_url != url:
                webpage = self._download_webpage(
                    video_alt_url, main_id,
                    note='Redirecting embed to main page', fatal=False) or webpage

        video_holder = get_element_by_class('video-holder', webpage) or ''
        if '>This video is a private video' in video_holder:
            self.raise_login_required(
                (clean_html(video_holder) or 'Private video').partition('\n')[0])

        uploader = self._html_search_regex(
            r'''(?s)<span\b[^>]*>Added by:\s*</span><a\b[^>]+\bclass\s*=\s*["']author\b[^>]+\bhref\s*=\s*["']https://thisvid\.com/members/([0-9]+/.{3,}?)\s*</a>''',
            webpage, 'uploader', default='')
        uploader = re.split(r'''/["'][^>]*>\s*''', uploader)
        if len(uploader) == 2:
            # id must be non-empty, uploader could be ''
            uploader_id, uploader = uploader
            uploader = uploader or None
        else:
            uploader_id = uploader = None

        return self.url_result(
            url, ie='Generic', url_transparent=True,
            title=title,
            age_limit=18,
            uploader=uploader,
            uploader_id=uploader_id)


class ThisVidPlaylistBaseIE(InfoExtractor):
    _PLAYLIST_URL_RE = None

    @classmethod
    def _find_urls(cls, html):
        for m in re.finditer(rf'''<a\b[^>]+\bhref\s*=\s*["'](?P<url>{cls._PLAYLIST_URL_RE}\b)[^>]+>''', html):
            yield m.group('url')

    def _generate_playlist_entries(self, url, playlist_id, html=None):
        page_url = url
        for page in itertools.count(1):
            if not html:
                html = self._download_webpage(
                    page_url, playlist_id, note=f'Downloading page {page}',
                    fatal=False) or ''

            yield from self._find_urls(html)

            next_page = get_element_by_class('pagination-next', html) or ''
            if next_page:
                # member list page
                next_page = urljoin(url, self._search_regex(
                    r'''<a\b[^>]+\bhref\s*=\s*("|')(?P<url>(?!#)(?:(?!\1).)+)''',
                    next_page, 'next page link', group='url', default=None))

            # in case a member page should have pagination-next with empty link, not just `else:`
            if next_page is None:
                # playlist page
                parsed_url = urllib.parse.urlparse(page_url)
                base_path, _, num = parsed_url.path.rpartition('/')
                num = int_or_none(num)
                if num is None:
                    base_path, num = parsed_url.path.rstrip('/'), 1
                parsed_url = parsed_url._replace(path=f'{base_path}/{num + 1}')
                next_page = urllib.parse.urlunparse(parsed_url)
                if page_url == next_page:
                    next_page = None

            if not next_page:
                return
            page_url, html = next_page, None

    def _make_playlist_result(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        title = re.split(
            r'(?i)\s*\|\s*ThisVid\.com\s*$',
            self._og_search_title(webpage, default=None)
            or self._html_search_regex(r'(?s)<title\b[^>]*>(.+?)</title', webpage, 'title', fatal=False) or '', maxsplit=1)[0] or None

        return self.playlist_from_matches(
            self._generate_playlist_entries(url, playlist_id, webpage),
            playlist_id=playlist_id, playlist_title=title, ie=ThisVidIE)


class ThisVidMemberIE(ThisVidPlaylistBaseIE):
    _VALID_URL = r'https?://thisvid\.com/members/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://thisvid.com/members/2140501/',
        'info_dict': {
            'id': '2140501',
            'title': 'Rafflesia\'s Profile',
        },
        'playlist_mincount': 16,
    }, {
        'url': 'https://thisvid.com/members/2140501/favourite_videos/',
        'info_dict': {
            'id': '2140501',
            'title': 'Rafflesia\'s Favourite Videos',
        },
        'playlist_mincount': 15,
    }, {
        'url': 'https://thisvid.com/members/636468/public_videos/',
        'info_dict': {
            'id': '636468',
            'title': 'Happymouth\'s Public Videos',
        },
        'playlist_mincount': 196,
    }]
    _PLAYLIST_URL_RE = ThisVidIE._VALID_URL

    def _real_extract(self, url):
        return self._make_playlist_result(url)


class ThisVidPlaylistIE(ThisVidPlaylistBaseIE):
    _VALID_URL = r'https?://thisvid\.com/playlist/(?P<id>\d+)/video/(?P<video_id>[A-Za-z0-9-]+)'
    _TESTS = [{
        'url': 'https://thisvid.com/playlist/6615/video/big-italian-booty-28/',
        'info_dict': {
            'id': '6615',
            'title': 'Underwear Stuff',
        },
        'playlist_mincount': 200,
    }, {
        'url': 'https://thisvid.com/playlist/6615/video/big-italian-booty-28/',
        'info_dict': {
            'id': '1072387',
            'ext': 'mp4',
            'title': 'Big Italian Booty 28',
            'description': 'md5:1bccf7b13765e18fb27bf764dba7ede2',
            'uploader_id': '367912',
            'uploader': 'Jcmusclefun',
            'age_limit': 18,
            'display_id': 'big-italian-booty-28',
            'thumbnail': r're:https?://\w+\.thisvid\.com/(?:[^/]+/)+1072387/preview\.jpg',
        },
        'params': {
            'noplaylist': True,
        },
    }]
    _PLAYLIST_URL_RE = _VALID_URL

    def _generate_playlist_entries(self, url, playlist_id, html=None):
        for wrapped_url in super()._generate_playlist_entries(url, playlist_id, html):
            video_id = re.match(self._VALID_URL, wrapped_url).group('video_id')
            yield urljoin(url, f'/videos/{video_id}/')

    def _real_extract(self, url):
        playlist_id, video_id = self._match_valid_url(url).group('id', 'video_id')

        if not self._yes_playlist(playlist_id, video_id):
            redirect_url = urljoin(url, f'/videos/{video_id}/')
            return self.url_result(redirect_url, ThisVidIE)

        result = self._make_playlist_result(url)

        # Fix duplicated title (`the title - the title` => `the title`)
        title = result['title']
        t_len = len(title)
        if t_len > 5 and t_len % 2 != 0:
            t_len = t_len // 2
            if title[t_len] == '-':
                first, second = map(str.strip, (title[:t_len], title[t_len + 1:]))
                if first and first == second:
                    result['title'] = first

        return result
