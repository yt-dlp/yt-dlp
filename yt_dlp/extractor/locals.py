import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    urljoin,
)


class LocalsIE(InfoExtractor):
    """
    Locals.com post extractor.

    Matches legacy community-subdomain post URLs:
        https://<community>.locals.com/post/<post_id>/<slug>
        https://<community>.locals.com/upost/<post_id>/<slug>

    Authentication: pass `--cookies` or `--cookies-from-browser` from a
    browser session that has visited the community subdomain while logged
    into locals.com. The community subdomain is a separate PHP app that
    uses its own PHPSESSID / auth_token / uid / uuid cookies, minted by a
    Rumble SSO exchange on first visit. Without those, posts play as a
    15-30 second preview (data-preview="true" in the HTML).
    """
    IE_NAME = 'locals'
    _VALID_URL = r'https?://(?P<community>[a-z0-9-]+)\.locals\.com/u?post/(?P<id>\d+)(?:/[^/?#]+)?'
    _TESTS = [{
        'url': 'https://predatorpoachers.locals.com/post/3078070/lance-armweak-predator-calls-police-summer-2019',
        'info_dict': {
            'id': '3078070',
            'ext': 'mp4',
            'title': str,
            'duration': 941,
            'uploader': 'predatorpoachers',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Requires predatorpoachers.locals.com subscriber cookies',
    }, {
        'url': 'https://predatorpoachers.locals.com/upost/3078070/lance-armweak-predator-calls-police-summer-2019',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        post_id = m.group('id')
        community = m.group('community')

        webpage = self._download_webpage(
            url, post_id, note='Downloading post page',
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
                ),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            })

        # The page contains one <video> block for the main post and several
        # for recommended/shared cards. Match on data-post-id to pick the right one.
        src_path = None
        preview = None
        duration = None
        for block in re.finditer(
                r'<video\b(?P<attrs>[^>]*)>\s*<source\b(?P<srcattrs>[^>]*)>',
                webpage, re.DOTALL):
            if self._search_regex(
                    r'data-post-id="(\d+)"', block.group('attrs'),
                    'post id', default=None) != post_id:
                continue
            src_path = self._search_regex(
                r'data-src="([^"]+\.m3u8)"', block.group('srcattrs'),
                'source', default=None)
            preview = self._search_regex(
                r'data-preview="(true|false)"', block.group('attrs'),
                'preview', default=None)
            duration = int_or_none(self._search_regex(
                r'data-duration="(\d+)"', block.group('attrs'),
                'duration', default=None))
            break

        if not src_path:
            raise ExtractorError(
                f'No video found on post {post_id}. Either this is a text-only '
                f'post, or your session cookies are not recognized on '
                f'{community}.locals.com. Visit the community subdomain in '
                f'your browser while logged in, then re-export cookies.',
                expected=True)

        if preview == 'true':
            self.report_warning(
                f'Only a 15-30 second preview is available. Your cookies are '
                f'not recognized as a subscriber on {community}.locals.com.')

        manifest_url = urljoin(f'https://{community}.locals.com', src_path)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            manifest_url, post_id, ext='mp4', m3u8_id='hls')

        title = self._og_search_title(webpage, default=None) or self._html_extract_title(webpage) or post_id
        title = re.sub(r'^Shared post\s*[-:]\s*', '', title).strip() or post_id

        return {
            'id': post_id,
            'title': title,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
            'uploader': community,
        }


class LocalsSitemapIE(InfoExtractor):
    """Enumerate every public post on a Locals community via its sitemap.xml."""
    IE_NAME = 'locals:sitemap'
    _VALID_URL = r'https?://(?P<community>[a-z0-9-]+)\.locals\.com/?(?:\?.*)?$'
    _TESTS = [{
        'url': 'https://predatorpoachers.locals.com/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        community = self._match_valid_url(url).group('community')
        sitemap = self._download_xml(
            f'https://{community}.locals.com/sitemap.xml', community,
            note='Downloading sitemap')
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = [
            loc.text for loc in sitemap.findall('.//s:url/s:loc', ns)
            if loc is not None and loc.text and '/post/' in loc.text
        ]
        return self.playlist_result(
            [self.url_result(u, LocalsIE) for u in urls],
            playlist_id=community,
            playlist_title=f'{community} (all public posts)')
