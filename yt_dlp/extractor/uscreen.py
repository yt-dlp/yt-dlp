import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    unescapeHTML,
)


class UscreenIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<host>[^/]+)/programs/(?P<slug>[^/?#]+)\?[^#]*cid=(?P<cid>\d+)[^#]*permalink=(?P<permalink>[^&#]+)'
    _NETRC_MACHINE = 'uscreen'
    _TESTS = [{
        'url': 'https://example.com/programs/collection-example?cid=2584778&permalink=session-5-sugar-push-a34d52',
        'info_dict': {
            'id': '1516845',
            'ext': 'mp4',
            'title': 'Basics 1 - Sugar Push',
            'series': 'Basics 1 ',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'Requires Uscreen account cookies',
    }]

    def _real_extract(self, url):
        host, slug, cid, permalink = self._match_valid_url(url).group('host', 'slug', 'cid', 'permalink')

        video_id = cid
        referer = f'https://{host}/programs/{slug}?cid={cid}&permalink={permalink}'

        webpage = self._download_webpage(
            f'https://{host}/programs/{slug}/program_content'
            f'?cid={cid}&permalink={permalink}'
            f'&playlist_position=thumbnails&preview=false',
            video_id,
            headers={
                'Referer': referer,
                'Turbo-Frame': 'program_collection',
            },
        )
        self.write_debug(f'Uscreen: fetched program_content for cid={cid}, permalink={permalink}')

        if not re.search(r'<video-player|turbo-frame|data-program-video', webpage):
            if any(re.search(p, webpage, re.IGNORECASE) for p in (
                r'Get Access Now', r'sign\s*in', r'Log\s*In', r'Unlock this',
            )):
                self.raise_login_required('This video requires authentication', method='cookies')
            if any(re.search(p, webpage, re.IGNORECASE) for p in (
                r'Subscribe', r'Upgrade', r'Join now', r'Purchase', r'No active subscription',
            )):
                raise ExtractorError('This video requires an active subscription', expected=True)
            self.raise_no_formats(
                'No video player found. This may not be a Uscreen video page', expected=True)

        video_player = self._search_regex(
            r'(<video-player[^>]*>)', webpage, 'video player tag', default=None)

        if not video_player:
            if any(re.search(p, webpage, re.IGNORECASE) for p in (
                r'Get Access Now', r'sign\s*in', r'Log\s*In', r'Unlock this',
            )):
                self.raise_login_required('This video requires authentication', method='cookies')
            if any(re.search(p, webpage, re.IGNORECASE) for p in (
                r'Subscribe', r'Upgrade', r'Join now', r'Purchase', r'No active subscription',
            )):
                raise ExtractorError('This video requires an active subscription', expected=True)
            raise ExtractorError('Could not find video player element', expected=True)

        self.write_debug('Uscreen: found <video-player> element')

        mux_data = self._search_json(
            r'''mux-data\s*=\s*['"]''', video_player, 'mux data',
            video_id, default={}, transform_source=unescapeHTML)
        stats_data = self._search_json(
            r'''data-program-video-stats-value\s*=\s*['"]''', video_player, 'video stats',
            video_id, default={}, transform_source=unescapeHTML)

        data_id = self._search_regex(
            r'data-id\s*=\s*["\'](\d+)["\']', video_player, 'data id', default=None)

        title = (
            traverse_obj(mux_data, 'video_title')
            or traverse_obj(stats_data, 'content_title')
            or self._html_search_regex(
                r'<h[12][^>]*class="[^"]*collection-title[^"]*"[^>]*>([^<]+)',
                webpage, 'title', default=permalink)
        )

        # Prefer HTML5 media entries if present
        entries = self._parse_html5_media_entries(
            f'https://{host}/programs/{slug}', webpage, video_id, m3u8_id='hls',
            _headers={'Referer': referer, 'Origin': f'https://{host}'})
        if entries:
            self.write_debug(f'Uscreen: parsed {len(entries)} HTML5 media entries')
            entry = entries[0]
            entry.update({
                'id': data_id or video_id,
                'title': title,
                'series': traverse_obj(stats_data, 'content_title'),
                'chapter_id': traverse_obj(stats_data, 'chapter_id', expected_type=str),
            })
            return entry

        m3u8_url = self._search_regex(
            r'<source\s+src="(https?://stream\.mux\.com/[^"]+\.m3u8[^"]*)"',
            webpage, 'm3u8 url')
        self.write_debug(f'Uscreen: using m3u8 url {m3u8_url}')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, 'mp4', m3u8_id='hls', headers={
                'Referer': referer,
                'Origin': f'https://{host}',
            })

        for fmt in formats:
            fmt.setdefault('http_headers', {})['Referer'] = referer

        return {
            'id': data_id or video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'series': traverse_obj(stats_data, 'content_title'),
            'chapter_id': traverse_obj(stats_data, 'chapter_id', expected_type=str),
        }


class UscreenCatalogIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<host>[^/]+)/catalog/?(?:[?#]|$)'
    _NETRC_MACHINE = 'uscreen'
    _TESTS = [{
        'url': 'https://example.uscreen.io/catalog',
        'info_dict': {
            'id': 'example.uscreen.io',
            'title': 'Catalog',
        },
        'playlist_mincount': 1,
        'skip': 'Requires Uscreen account cookies',
    }]

    def _download_api_webpage(self, url, video_id, *, referer, api_origin, note=None):
        return self._download_webpage(url, video_id, note=note, headers={
            'Referer': referer,
            'X-Fastly-Origin': api_origin,
        })

    def _real_extract(self, url):
        host = self._match_valid_url(url).group('host')
        base_url = f'https://{host}'

        webpage, urlh = self._download_webpage_handle(f'{base_url}/catalog', host)
        # yt-dlp networking responses expose .url; avoid deprecated geturl()
        final_url = (getattr(urlh, 'url', None) if urlh else None) or ''
        final_host = urllib.parse.urlparse(final_url).hostname or ''

        # Some Uscreen subdomains redirect to the Uscreen marketing site or to an
        # "unavailable" landing page when the storefront is disabled/unconfigured.
        if final_host and final_host != host:
            if final_host.endswith('uscreen.tv') or re.search(r'>\s*This store unavailable\s*<', webpage):
                raise ExtractorError(
                    f'This Uscreen storefront appears to be unavailable (redirected to {final_host})',
                    expected=True)

        api_origin = self._search_regex(
            r'window\.apiOrigin\s*=\s*"([^"]+)"', webpage, 'api origin', default=None)
        if not api_origin:
            raise ExtractorError('Could not find api origin (apiOrigin)', expected=True)

        initial_categories_url = self._search_regex(
            r'<turbo-frame[^>]+\bid="catalog_content"[^>]+\bsrc="([^"]+)"',
            webpage, 'catalog content url', default=None)
        initial_categories_url = (
            unescapeHTML(initial_categories_url)
            if initial_categories_url else
            'https://api.uscreencdn.com/catalog/initial_categories'
            '?continue_watching=false&my_library=true&preview=false&user=true'
        )

        initial_categories = self._download_api_webpage(
            initial_categories_url, host,
            referer=f'{base_url}/catalog', api_origin=api_origin,
            note='Downloading catalog categories')

        # Extract categories in the order shown on the catalog page
        categories = []
        seen_category_ids = set()
        for mobj in re.finditer(r'''(?sx)
            <div[^>]+\bclass="category-group"[^>]*\bdata-category-id="(?P<id>\d+)"[^>]*>
            .*?
            <a[^>]+\bclass="category-title[^"]*"[^>]+\bhref="(?P<href>[^"]+)"[^>]*>
              (?P<title>[^<]+)
            </a>
        ''', initial_categories):
            category_id = mobj.group('id')
            if category_id in seen_category_ids:
                continue
            seen_category_ids.add(category_id)
            href = unescapeHTML(mobj.group('href'))
            title = unescapeHTML(mobj.group('title')).strip()
            if not href.startswith('/categories/'):
                continue
            categories.append({
                'id': category_id,
                'title': title,
                'href': href,
            })

        if not categories:
            self.raise_login_required(
                'No categories found. You may need to authenticate', method='cookies')

        seen_entries = set()

        def entries():
            for category in categories:
                category_title = category['title']
                category_href = category['href'].rstrip('/')
                category_slug = category_href.rsplit('/', 1)[-1]
                category_url = f'{base_url}{category_href}'

                category_content = self._download_api_webpage(
                    'https://api.uscreencdn.com/categories/'
                    f'{category_slug}/search?action=show&controller=storefront%2Fcategories'
                    f'&format=turbo_stream&id={category_slug}',
                    category_slug,
                    referer=category_url, api_origin=api_origin,
                    note=f'Downloading category page for {category_title}')

                programs = []
                seen_programs = set()
                for mobj in re.finditer(
                    r'''(?x)href=["\'"](?:/programs/(?P<slug>[^/?#"\']+)\?[^"'#]*\bcategory_id=(?P<category_id>\d+)[^"']*)["\']''',
                    category_content):
                    program_slug = mobj.group('slug')
                    program_category_id = mobj.group('category_id')
                    if program_slug in seen_programs:
                        continue
                    seen_programs.add(program_slug)
                    programs.append({
                        'slug': program_slug,
                        'category_id': program_category_id,
                    })

                if not programs:
                    continue

                for program in programs:
                    program_slug = program['slug']
                    program_category_id = program['category_id']

                    program_content = self._download_webpage(
                        f'{base_url}/programs/{program_slug}/program_content'
                        '?playlist_position=thumbnails&preview=false',
                        program_slug,
                        headers={
                            'Referer': f'{base_url}/programs/{program_slug}',
                            'Turbo-Frame': 'program_collection',
                        },
                    )

                    if not re.search(r'data-cid|turbo-frame|video-player|collection-title', program_content):
                        if any(re.search(p, program_content, re.IGNORECASE) for p in (
                            r'Get Access Now', r'sign\s*in', r'Log\s*In', r'Unlock this',
                        )):
                            self.raise_login_required(
                                'This collection requires authentication', method='cookies')
                        if any(re.search(p, program_content, re.IGNORECASE) for p in (
                            r'Subscribe', r'Upgrade', r'Join now', r'Purchase', r'No active subscription',
                        )):
                            raise ExtractorError('This collection requires an active subscription', expected=True)

                    collection_title = self._html_search_regex(
                        r'<h1[^>]*class="[^"]*collection-title[^"]*"[^>]*>([^<]+)',
                        program_content, 'collection title', default=program_slug)

                    pairs = re.findall(
                        r'data-cid=["\'](\d+)["\'][^>]*data-permalink=["\']([^"\']+)["\']',
                        program_content)

                    if not pairs:
                        pairs = [
                            (cid, perm) for perm, cid in re.findall(
                                r'data-permalink=["\']([^"\']+)["\'][^>]*data-cid=["\'](\d+)["\']',
                                program_content)
                        ]

                    if not pairs:
                        self.raise_login_required(
                            'No video entries found. You may need to authenticate', method='cookies')

                    seen_pairs = set()
                    unique_pairs = []
                    for cid, permalink in pairs:
                        if (cid, permalink) in seen_pairs:
                            continue
                        seen_pairs.add((cid, permalink))
                        unique_pairs.append((cid, permalink))

                    for collection_index, (cid, permalink) in enumerate(unique_pairs, start=1):
                        entry_key = (category_slug, program_slug, cid, permalink)
                        if entry_key in seen_entries:
                            continue
                        seen_entries.add(entry_key)

                        yield {
                            '_type': 'url_transparent',
                            'url': f'{base_url}/programs/{program_slug}?cid={cid}&permalink={permalink}',
                            'ie_key': UscreenIE.ie_key(),
                            'category': category_title,
                            'category_id': program_category_id,
                            'collection': collection_title,
                            'collection_id': program_slug,
                            'collection_index': collection_index,
                            'collection_count': len(unique_pairs),
                        }

        return self.playlist_result(entries(), host, 'Catalog')


class UscreenCollectionIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<host>[^/]+)/programs/(?P<slug>[^/?#]+)/?(?:[?#]|$)'
    _NETRC_MACHINE = 'uscreen'
    _TESTS = [{
        'url': 'https://example.com/programs/collection-example',
        'info_dict': {
            'id': 'collection-example',
            'title': 'Basics 1',
        },
        'playlist_mincount': 11,
        'skip': 'Requires Uscreen account cookies',
    }]

    @classmethod
    def suitable(cls, url):
        return False if UscreenIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        host, slug = self._match_valid_url(url).group('host', 'slug')

        webpage = self._download_webpage(
            f'https://{host}/programs/{slug}/program_content'
            f'?playlist_position=thumbnails&preview=false',
            slug,
            headers={
                'Referer': f'https://{host}/programs/{slug}',
                'Turbo-Frame': 'program_collection',
            },
        )
        self.write_debug(f'UscreenCollection: fetched program_content for slug={slug}')

        if not re.search(r'data-cid|turbo-frame|video-player|collection-title', webpage):
            if any(re.search(p, webpage, re.IGNORECASE) for p in (
                r'Get Access Now', r'sign\s*in', r'Log\s*In', r'Unlock this',
            )):
                self.raise_login_required('This collection requires authentication', method='cookies')
            if any(re.search(p, webpage, re.IGNORECASE) for p in (
                r'Subscribe', r'Upgrade', r'Join now', r'Purchase', r'No active subscription',
            )):
                raise ExtractorError('This collection requires an active subscription', expected=True)
            raise ExtractorError(
                'No collection content found. This may not be a Uscreen page', expected=True)

        collection_title = self._html_search_regex(
            r'<h1[^>]*class="[^"]*collection-title[^"]*"[^>]*>([^<]+)',
            webpage, 'collection title', default=slug)

        pairs = re.findall(
            r'data-cid=["\'](\d+)["\'][^>]*data-permalink=["\']([^"\']+)["\']',
            webpage)

        if not pairs:
            pairs = [
                (cid, perm) for perm, cid in re.findall(
                    r'data-permalink=["\']([^"\']+)["\'][^>]*data-cid=["\'](\d+)["\']',
                    webpage)
            ]

        if not pairs:
            self.raise_login_required(
                'No video entries found. You may need to authenticate', method='cookies')

        self.write_debug(f'UscreenCollection: found {len(pairs)} cid/permalink pairs')
        seen = set()
        unique_pairs = []
        for cid, permalink in pairs:
            if (cid, permalink) not in seen:
                seen.add((cid, permalink))
                unique_pairs.append((cid, permalink))

        entries = [
            self.url_result(
                f'https://{host}/programs/{slug}?cid={cid}&permalink={permalink}',
                ie=UscreenIE, video_id=cid, video_title=permalink)
            for cid, permalink in unique_pairs
        ]

        return self.playlist_result(entries, slug, collection_title)
