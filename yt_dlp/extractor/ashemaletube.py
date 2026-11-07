import functools
import json
import random
import shutil
import subprocess
import urllib.parse

from .common import InfoExtractor
from ..networking import Request
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    merge_dicts,
    parse_duration,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class AShemaleTubeIE(InfoExtractor):
    IE_NAME = 'ashemaletube'
    _VALID_URL = r'https?://(?:www\.)?ashemaletube\.[a-z]+/videos/(?P<id>\d+)(?:/(?P<display_id>[^/?#]+))?'
    _TESTS = [{
        'url': 'https://www.ashemaletube.me/videos/1263664/femboy-nicoolwzz-nilly-2',
        'info_dict': {
            'id': '1263664',
            'display_id': 'femboy-nicoolwzz-nilly-2',
            'ext': 'mp4',
            'title': 'Femboy Nicoolwzz Nilly 2',
            'thumbnail': r're:https?://.+\.jpg',
            'duration': 1639,
            'age_limit': 18,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.ashemaletube.me/videos/1263670/sabrina-prezotte',
        'only_matching': True,
    }, {
        'url': 'https://www.ashemaletube.me/videos/1261470/cute-asian-femboy-princess-with-braces-m33n/',
        'only_matching': True,
    }, {
        'url': 'https://ashemaletube.me/videos/1263664',
        'only_matching': True,
    }]

    _THROTTLE_STATUSES = (403, 429)

    def _retry_throttled(self, func, video_id):
        """The site intermittently answers valid requests with 403/429, so back off and retry"""
        has_sleep = bool(self.get_param('retry_sleep_functions', {}).get('extractor'))
        for retry in self.RetryManager():
            try:
                return func()
            except ExtractorError as e:
                if not (isinstance(e.cause, HTTPError) and e.cause.status in self._THROTTLE_STATUSES):
                    raise
                retry.error = e
                # Retrying at once is pointless, so back off unless --retry-sleep was given
                if not has_sleep and retry.attempt <= retry.retries:
                    self._sleep(min(2 ** retry.attempt, 16) + random.random(), video_id)

    def _probe_hls_size(self, fmt, video_id, headers):
        """The master playlist only has nominal sizes, which are wrong for
        portrait or odd-ratio streams, so read the real one from the first segment.
        Returns None if the size can't be read. Raises ExtractorError if the site throttles"""
        playlist = self._retry_throttled(functools.partial(
            self._download_webpage, fmt['url'], video_id,
            f'Probing {fmt["format_id"]}', headers=headers), video_id)
        segment = next((
            line.strip() for line in playlist.splitlines()
            if line.strip() and not line.startswith('#')), None)
        if not segment:
            return None
        res = self._retry_throttled(functools.partial(
            self._request_webpage,
            Request(urllib.parse.urljoin(fmt['url'], segment), headers={
                **headers, 'Range': 'bytes=0-262143'}),
            video_id, note=False), video_id)
        try:
            data = res.read(262144)
        finally:
            res.close()
        try:
            probed = subprocess.run(
                [shutil.which('ffprobe'), '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=width,height', '-of', 'json', '-'],
                input=data, capture_output=True, timeout=30, check=False)
            # MPEG-TS segments list the stream under programs, other containers under streams
            stream = traverse_obj(
                json.loads(probed.stdout or b'{}'),
                ('streams', 0), ('programs', 0, 'streams', 0)) or {}
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            self.write_debug(f'Size probe failed for {fmt["format_id"]}: {e}')
            return None
        if stream.get('width') and stream.get('height'):
            return stream['width'], stream['height']
        return None

    def _probe_hls_sizes(self, formats, video_id, headers):
        # Sizes are cached because a front end such as MeTube extracts every URL twice
        cache_key = f'size-{video_id}'
        sizes = self.cache.load(self.ie_key(), cache_key) or {}
        changed = False
        for fmt in formats:
            if not str(fmt.get('protocol')).startswith('m3u8'):
                continue
            if fmt['format_id'] not in sizes:
                try:
                    size = self._probe_hls_size(fmt, video_id, headers)
                except ExtractorError as e:
                    # Stop probing instead of making a throttled site even slower
                    self.report_warning(f'Skipping size probe of the remaining formats: {e.msg}', video_id)
                    break
                if not size:
                    continue
                sizes[fmt['format_id']] = size
                changed = True
            fmt['width'], fmt['height'] = sizes[fmt['format_id']]
        if changed:
            self.cache.store(self.ie_key(), cache_key, sizes)

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        display_id = display_id or video_id

        webpage, urlh = self._retry_throttled(
            functools.partial(self._download_webpage_handle, url, display_id), display_id)
        # Only trust the redirect target if it is still a video page
        if redirected := self._match_valid_url(urlh.url):
            video_id = redirected.group('id')

        sources = self._search_json(
            r'sources\s*:', webpage, 'player sources', display_id, default=None)
        if not sources:
            raise ExtractorError(
                'No player sources found; the video may require a login or be unavailable',
                expected=True)

        headers = {'Referer': urlh.url}
        formats = []
        hls_error = None
        hls_urls = [sources.get('hlsAuto'), *traverse_obj(sources, ('hls', ..., 'src'))]
        for src in filter(None, map(url_or_none, hls_urls)):
            try:
                formats.extend(self._retry_throttled(functools.partial(
                    self._extract_m3u8_formats, src, display_id, 'mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls', headers=headers), display_id))
            except ExtractorError as e:
                hls_error = e
                self.report_warning(e.msg, display_id)
        for item in traverse_obj(sources, ('mp4', lambda _, v: url_or_none(v.get('src')))):
            formats.append({
                'url': item['src'],
                'format_id': join_nonempty('mp4', item.get('quality')),
                'height': int_or_none(item.get('quality')),
            })
        if not formats:
            if hls_error and isinstance(hls_error.cause, HTTPError):
                raise ExtractorError(
                    f'The site refused the stream request (HTTP {hls_error.cause.status}), '
                    'it is probably throttling; try again in a few minutes', expected=True)
            raise ExtractorError('Could not extract any video formats')

        for fmt in formats:
            fmt.setdefault('http_headers', headers)
        if shutil.which('ffprobe') and self._configuration_arg('probe', ['1'])[0] != '0':
            self._probe_hls_sizes(formats, display_id, headers)

        json_ld = self._search_json_ld(webpage, display_id, default={})
        duration = parse_duration(self._html_search_meta('duration', webpage, default=None))

        return merge_dicts(json_ld, {
            'id': video_id,
            'display_id': display_id,
            'title': self._og_search_title(webpage, default=None) or display_id,
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'duration': duration or int_or_none(self._search_regex(
                r'videoDuration\s*:\s*(\d+)', webpage, 'duration', default=None)),
            'formats': formats,
            'age_limit': 18,
        })
