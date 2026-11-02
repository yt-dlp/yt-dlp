import json
import shutil
import subprocess
import urllib.parse

from .common import InfoExtractor
from ..networking import Request
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
            'description': 'Anal, Teen (18+), Cumshot, Femboy, Fuck Femboy, Brazilian Femboy',
            'thumbnail': r're:https?://.+\.jpg',
            'duration': 1639,
            'timestamp': 1793478062,
            'upload_date': '20261031',
            'view_count': int,
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

    def _probe_hls_size(self, fmt, video_id, headers):
        """The master playlist only has nominal sizes, which are wrong for
        portrait or odd-ratio streams, so read the real one from the first segment."""
        ffprobe = shutil.which('ffprobe')
        if not ffprobe:
            return
        playlist = self._download_webpage(
            fmt['url'], video_id, f'Probing {fmt["format_id"]}', fatal=False, headers=headers)
        segment = next((
            line.strip() for line in (playlist or '').splitlines()
            if line.strip() and not line.startswith('#')), None)
        if not segment:
            return
        try:
            res = self._request_webpage(
                Request(urllib.parse.urljoin(fmt['url'], segment), headers={
                    **headers, 'Range': 'bytes=0-262143'}),
                video_id, note=False, errnote=False)
            probed = subprocess.run(
                [ffprobe, '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=width,height', '-of', 'json', '-'],
                input=res.read(262144), capture_output=True, timeout=30, check=False)
            stream = traverse_obj(json.loads(probed.stdout or b'{}'), ('streams', 0)) or {}
        except Exception as e:
            self.write_debug(f'Size probe failed for {fmt["format_id"]}: {e}')
            return
        if stream.get('width') and stream.get('height'):
            fmt['width'], fmt['height'] = stream['width'], stream['height']

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        display_id = display_id or video_id

        webpage, urlh = self._download_webpage_handle(url, display_id)
        video_id = self._match_id(urlh.url)

        sources = self._search_json(
            r'sources\s*:', webpage, 'player sources', display_id, default=None)
        if not sources:
            raise ExtractorError(
                'No player sources found; the video may require a login or be unavailable',
                expected=True)

        headers = {'Referer': urlh.url}
        formats = []
        hls_urls = [sources.get('hlsAuto'), *traverse_obj(sources, ('hls', ..., 'src'))]
        for src in filter(None, map(url_or_none, hls_urls)):
            formats.extend(self._extract_m3u8_formats(
                src, display_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=False, headers=headers))
        for item in traverse_obj(sources, ('mp4', lambda _, v: url_or_none(v.get('src')))):
            formats.append({
                'url': item['src'],
                'format_id': join_nonempty('mp4', item.get('quality')),
                'height': int_or_none(item.get('quality'), default=None),
            })
        if not formats:
            raise ExtractorError('Could not extract any video formats')

        probe = self._configuration_arg('probe', ['1'])[0] != '0'
        for fmt in formats:
            fmt.setdefault('http_headers', headers)
            if probe and str(fmt.get('protocol')).startswith('m3u8'):
                self._probe_hls_size(fmt, display_id, headers)

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
