from .common import InfoExtractor
from ..utils import (
    int_or_none,
    qualities,
    try_call,
    try_get,
    ExtractorError,
)
from ..compat import compat_str


class WhoWatchIE(InfoExtractor):
    IE_NAME = 'whowatch'
    _VALID_URL = r'https?://whowatch\.tv/viewer/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://whowatch.tv/viewer/21450171',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._download_webpage(url, video_id)
        metadata = self._download_json('https://api.whowatch.tv/lives/%s' % video_id, video_id)
        live_data = self._download_json('https://api.whowatch.tv/lives/%s/play' % video_id, video_id)

        title = try_call(
            lambda: live_data['share_info']['live_title'][1:-1],
            lambda: metadata['live']['title'],
            expected_type=str)

        hls_url = live_data.get('hls_url')
        if not hls_url:
            raise ExtractorError(live_data.get('error_message') or 'The user is offline.', expected=True)

        QUALITIES = qualities(['low', 'medium', 'high', 'veryhigh'])
        formats = []

        for i, fmt in enumerate(live_data.get('streams') or []):
            name = fmt.get('quality') or fmt.get('name') or compat_str(i)
            hls_url = fmt.get('hls_url')
            rtmp_url = fmt.get('rtmp_url')
            audio_only = fmt.get('audio_only')
            quality = QUALITIES(fmt.get('quality'))

            if hls_url:
                hls_fmts = self._extract_m3u8_formats(
                    hls_url, video_id, ext='mp4', m3u8_id='hls-%s' % name, quality=quality)
                formats.extend(hls_fmts)
            else:
                hls_fmts = []

            # RTMP url for audio_only is same as high format, so skip it
            if rtmp_url and not audio_only:
                formats.append({
                    'url': rtmp_url,
                    'format_id': 'rtmp-%s' % name,
                    'ext': 'mp4',
                    'protocol': 'rtmp_ffmpeg',  # ffmpeg can, while rtmpdump can't
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'quality': quality,
                    'format_note': fmt.get('label'),
                    # note: HLS and RTMP have same resolution for now, so it's acceptable
                    'width': try_get(hls_fmts, lambda x: x[0]['width'], int),
                    'height': try_get(hls_fmts, lambda x: x[0]['height'], int),
                })

        # This contains the same formats as the above manifests and is used only as a fallback
        formats.extend(self._extract_m3u8_formats(
            hls_url, video_id, ext='mp4', m3u8_id='hls'))
        self._remove_duplicate_formats(formats)
        self._sort_formats(formats)

        uploader_url = try_get(metadata, lambda x: x['live']['user']['user_path'], compat_str)
        if uploader_url:
            uploader_url = 'https://whowatch.tv/profile/%s' % uploader_url
        uploader_id = compat_str(try_get(metadata, lambda x: x['live']['user']['id'], int))
        uploader = try_get(metadata, lambda x: x['live']['user']['name'], compat_str)
        thumbnail = try_get(metadata, lambda x: x['live']['latest_thumbnail_url'], compat_str)
        timestamp = int_or_none(try_get(metadata, lambda x: x['live']['started_at'], int), scale=1000)
        view_count = try_get(metadata, lambda x: x['live']['total_view_count'], int)
        comment_count = try_get(metadata, lambda x: x['live']['comment_count'], int)

        return {
            'id': video_id,
            'title': title,
            'uploader_id': uploader_id,
            'uploader_url': uploader_url,
            'uploader': uploader,
            'formats': formats,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'view_count': view_count,
            'comment_count': comment_count,
            'is_live': True,
        }
