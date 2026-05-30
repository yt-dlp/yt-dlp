import json
import re
import time
import urllib.parse
from http.cookiejar import Cookie

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unified_strdate,
)
from ..utils.traversal import traverse_obj


class BeeldenGeluidIE(InfoExtractor):
    _VALID_URL = r'https?://schatkamer\.beeldengeluid\.nl/serie/(?P<series_id>[^/]+)/(?P<series_slug>[^/]+)/aflevering/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://schatkamer.beeldengeluid.nl/serie/2101608030021443931/lingo/aflevering/2101608040029173231',
        'info_dict': {
            'id': '2101608040029173231',
            'ext': 'mp4',
            'title': 'LINGO - LINGO',
            'description': 'md5:1b354b4f3c1961292b6b6f6f2eb7479a',
            'upload_date': '19890105',
            'duration': 1620,
            'thumbnail': r're:^https?://.*\.jpg$',
            'series': 'LINGO',
            'episode': 'LINGO',
        },
    }]

    def _prepare_cloudfront_request(self, m3u8_url):
        """Extract CloudFront signed URL parameters and set them as path-scoped cookies.
        Sets cookies in the cookie jar and returns the base URL.
        """
        parsed = urllib.parse.urlparse(m3u8_url)
        params = urllib.parse.parse_qs(parsed.query)
        domain = parsed.hostname

        # Extract asset root path
        path_parts = parsed.path.split('/')
        cookie_path = f'/{path_parts[1]}/' if len(path_parts) > 1 else '/'

        for param_name in ('CloudFront-Policy', 'CloudFront-Signature', 'CloudFront-Key-Pair-Id'):
            value = params.get(param_name, [None])[0]
            if value:
                cookie = Cookie(
                    version=0, name=param_name, value=value,
                    port=None, port_specified=False,
                    domain=f'.{domain.split(".", 1)[1]}', domain_specified=True, domain_initial_dot=True,
                    path=cookie_path, path_specified=True,
                    secure=True, expires=int(time.time()) + 3600,
                    discard=False, comment=None, comment_url=None, rest={}, rfc2109=False,
                )
                self._downloader.cookiejar.set_cookie(cookie)

        return f'{parsed.scheme}://{parsed.netloc}{parsed.path}'

    _STREAM_ACTION_ID = '6099b784686c7da80c0e418528160e82b7eced6e34'

    def _fetch_fresh_streams(self, url, video_id):
        """Fetch fresh stream URLs via Next.js Server Action (getProgramStreamById)."""
        data = self._download_webpage(
            url, video_id,
            note='Fetching fresh stream data via server action',
            data=json.dumps([video_id, False]).encode(),
            headers={
                'Content-Type': 'text/plain;charset=UTF-8',
                'Next-Action': self._STREAM_ACTION_ID,
                'Accept': 'text/x-component',
            })

        # Response is RSC flight data with T-chunks: "N:Thex_size,<content>"
        # The hex_size indicates exact byte count of content, preventing boundary corruption
        m3u8_urls = []
        for m in re.finditer(r'(\d+):T([0-9a-f]+),', data):
            size = int(m.group(2), 16)
            start = m.end()
            content = data[start:start + size]
            if 'sk-video.cdn.beeldengeluid.nl' in content and '.m3u8' in content:
                m3u8_urls.append(content.strip())

        return m3u8_urls

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        # Fetch metadata from BFF API
        meta = self._download_json(
            f'https://schatkamer.beeldengeluid.nl/api/media/bff/programs/{video_id}',
            video_id, note='Downloading metadata')
        program = meta.get('data', meta)

        # Fetch fresh stream URLs via Server Action
        m3u8_urls = self._fetch_fresh_streams(url, video_id)

        if not m3u8_urls:
            self.raise_no_formats('No stream URLs found')

        # Extract formats from each stream URL
        all_stream_formats = []
        for m3u8_raw in m3u8_urls:
            m3u8_url = m3u8_raw.replace('\\u0026', '&')

            # CDN requires CloudFront cookies for authentication.
            # Set path-scoped cookies in jar, then request with base URL only.
            base_m3u8_url = self._prepare_cloudfront_request(m3u8_url)

            fmts = self._extract_m3u8_formats(
                base_m3u8_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            if fmts:
                all_stream_formats.append(fmts)

        if not all_stream_formats:
            self.raise_no_formats('No working stream found')

        # Extract metadata from BFF response
        series_title = traverse_obj(program, ('series', 'title'))
        episode_title = program.get('name')
        title = f'{series_title} - {episode_title}' if series_title and episode_title else (
            series_title or episode_title or video_id)

        thumbnail = traverse_obj(program, ('image', 'url'))
        duration = int_or_none(program.get('duration'))
        # duration from API is in minutes, convert to seconds
        if duration:
            duration = duration * 60

        common_info = {
            'description': program.get('description'),
            'upload_date': unified_strdate(program.get('publishedAt')),
            'thumbnail': thumbnail,
            'series': series_title,
            'episode': episode_title,
        }

        # Single stream: return directly
        if len(all_stream_formats) == 1:
            return {
                'id': video_id,
                'title': title,
                'duration': duration,
                'formats': all_stream_formats[0],
                **common_info,
            }

        # Multiple streams: return as playlist with _1, _2 suffixes
        entries = []
        for idx, fmts in enumerate(all_stream_formats, 1):
            entries.append({
                'id': f'{video_id}_{idx}',
                'title': f'{title}_{idx}',
                'duration': duration,
                'formats': fmts,
                **common_info,
            })

        return self.playlist_result(entries, video_id, title)
