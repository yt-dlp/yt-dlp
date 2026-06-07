import re

from .common import InfoExtractor
from .generic import GenericIE
from ..utils import (
    int_or_none,
    js_to_json,
    parse_duration,
    parse_resolution,
    unified_strdate,
    urljoin,
)


class BoundHubIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?boundhub\.com/videos/(?P<id>\d+)(?:/(?P<display_id>[^/?#]+))?'
    _TESTS = [{
        'url': 'https://www.boundhub.com/videos/632709/body-harness-tutorial/',
        'md5': '31cdb5ae326cdd200ae8ff845fef342c',
        'info_dict': {
            'id': '632709',
            'ext': 'mp4',
            'display_id': 'body-harness-tutorial',
            'title': 'BoundHub - Body Harness Tutorial',
            'description': 'Tutorial for Shibari Rope Corset Suspender Body Harness',
            'thumbnail': r're:https?://.*\.jpg$',
            'view_count': int,
            'categories': list,
            'age_limit': 18,
        },
    }]
    _NETRC_MACHINE = 'boundhub'

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        webpage = self._download_webpage(url, video_id, impersonate=True)

        # Extract KVS player flashvars
        kvs_info = self._extract_kvs(url, webpage, video_id)

        title = (
            self._html_search_regex(
                r'<h1[^>]*>([^<]+)</h1>', webpage, 'title', default=None)
            or self._og_search_title(webpage, default=None)
            or kvs_info.get('title')
        )

        description = (
            self._og_search_description(webpage, default=None)
            or self._html_search_meta('description', webpage, default=None)
        )

        thumbnail = (
            kvs_info.get('thumbnail')
            or self._og_search_thumbnail(webpage, default=None)
        )

        uploader = self._html_search_regex(
            r'<span[^>]*class="[^"]*username[^"]*"[^>]*>([^<]+)</span>',
            webpage, 'uploader', default=None)

        duration = parse_duration(self._search_regex(
            r'<span[^>]*class="[^"]*duration[^"]*"[^>]*>([^<]+)</span>',
            webpage, 'duration', default=None))

        view_count = int_or_none(self._search_regex(
            r'([\d,]+)\s*(?:views|plays)',
            webpage, 'view count', default=None, flags=re.IGNORECASE))

        upload_date = unified_strdate(self._search_regex(
            r'(?:Added|Uploaded)[:\s]*([^<]+)',
            webpage, 'upload date', default=None))

        categories = re.findall(
            r'<a[^>]+href="[^"]*categories/[^"]*"[^>]*>([^<]+)</a>',
            webpage)

        return {
            **kvs_info,
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'duration': duration,
            'view_count': view_count,
            'upload_date': upload_date,
            'categories': categories or None,
            'age_limit': 18,
        }

    def _extract_kvs(self, url, webpage, video_id):
        flashvars = self._search_json(
            r'(?s:<script\b[^>]*>.*?var\s+flashvars\s*=)',
            webpage, 'flashvars', video_id, transform_source=js_to_json)

        display_id = self._search_regex(
            r'(?:<link href="https?://[^"]+/(.+?)/?" rel="canonical"\s*/?>'
            r'|<link rel="canonical" href="https?://[^"]+/(.+?)/?"\s*/?>)',
            webpage, 'display_id', fatal=False)
        title = self._html_search_regex(
            r'<(?:h1|title)>(?:Video: )?(.+?)</(?:h1|title)>', webpage, 'title', default=None)

        thumbnail = flashvars.get('preview_url', '')
        if thumbnail.startswith('//'):
            protocol, _, _ = url.partition('/')
            thumbnail = protocol + thumbnail

        url_keys = list(filter(re.compile(r'^video_(?:url|alt_url\d*)$').match, flashvars.keys()))
        formats = []
        for key in url_keys:
            if '/get_file/' not in flashvars[key]:
                continue
            format_id = flashvars.get(f'{key}_text', key)
            # Use GenericIE's classmethod for URL deobfuscation
            real_url = GenericIE._kvs_get_real_url(flashvars[key], flashvars['license_code'])
            formats.append({
                'url': urljoin(url, real_url),
                'format_id': format_id,
                'ext': 'mp4',
                **(parse_resolution(format_id) or parse_resolution(flashvars[key])),
                'http_headers': {'Referer': url},
                'impersonate': True,
            })
            if not formats[-1].get('height'):
                formats[-1]['quality'] = 1

        return {
            'id': flashvars.get('video_id', video_id),
            'display_id': display_id,
            'title': title,
            'thumbnail': urljoin(url, thumbnail) if thumbnail else None,
            'formats': formats,
        }


class BoundHubPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?boundhub\.com/playlists/(?P<id>\d+)(?:/(?P<display_id>[^/?#]+))?'
    _TESTS = [{
        'url': 'https://www.boundhub.com/playlists/230107/test132/',
        'info_dict': {
            'id': '230107',
            'title': 'test132',
        },
        'playlist_mincount': 3,
    }]

    def _real_extract(self, url):
        playlist_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        webpage = self._download_webpage(url, playlist_id, impersonate=True)

        title = (
            self._html_search_regex(
                r'<h1[^>]*>([^<]+)</h1>', webpage, 'title', default=None)
            or self._og_search_title(webpage, default=None)
            or display_id
        )

        entries = []
        for mobj in re.finditer(
                r'<a[^>]+href=["\'](?P<url>https?://(?:www\.)?boundhub\.com/videos/(?P<id>\d+)/[^"\']+)["\']',
                webpage):
            entries.append(self.url_result(
                mobj.group('url'),
                ie=BoundHubIE.ie_key(),
                video_id=mobj.group('id')))

        # Handle pagination if present
        next_page = self._search_regex(
            r'<a[^>]+class="[^"]*next[^"]*"[^>]+href="([^"]+)"',
            webpage, 'next page', default=None)

        if next_page:
            next_page_url = urljoin(url, next_page)
            next_page_results = self._real_extract(next_page_url)
            entries.extend(next_page_results.get('entries', []))

        return self.playlist_result(entries, playlist_id, title)
