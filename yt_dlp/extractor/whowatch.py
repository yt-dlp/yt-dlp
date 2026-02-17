from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
    traverse_obj,
)


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
        metadata = self._download_json(f'https://api.whowatch.tv/lives/{video_id}', video_id)
        live_data = self._download_json(f'https://api.whowatch.tv/lives/{video_id}/play', video_id)

        title = traverse_obj(live_data, ('share_info', 'live_title', {lambda x: x[1:-1]}), expected_type=str) or traverse_obj(metadata, ('live', 'title'), expected_type=str)

        hls_url = live_data.get('hls_url')
        if not hls_url:
            raise ExtractorError(live_data.get('error_message') or 'The user is offline.', expected=True)

        QUALITIES = qualities(['low', 'medium', 'high', 'veryhigh'])
        formats = []

        for i, fmt in enumerate(live_data.get('streams') or []):
            name = fmt.get('quality') or fmt.get('name') or str(i)
            hls_url = fmt.get('hls_url')
            rtmp_url = fmt.get('rtmp_url')
            audio_only = fmt.get('audio_only')
            quality = QUALITIES(fmt.get('quality'))

            if hls_url:
                hls_fmts = self._extract_m3u8_formats(
                    hls_url, video_id, ext='mp4', m3u8_id=f'hls-{name}', quality=quality)
                formats.extend(hls_fmts)
            else:
                hls_fmts = []

            # RTMP url for audio_only is same as high format, so skip it
            if rtmp_url and not audio_only:
                formats.append({
                    'url': rtmp_url,
                    'format_id': f'rtmp-{name}',
                    'ext': 'mp4',
                    'protocol': 'rtmp_ffmpeg',  # ffmpeg can, while rtmpdump can't
                    'vcodec': 'h264',
                    'acodec': 'aac',
                    'quality': quality,
                    'format_note': fmt.get('label'),
                    # note: HLS and RTMP have same resolution for now, so it's acceptable
                    'width': traverse_obj(hls_fmts, (0, 'width'), expected_type=int),
                    'height': traverse_obj(hls_fmts, (0, 'height'), expected_type=int),
                })

        # This contains the same formats as the above manifests and is used only as a fallback
        formats.extend(self._extract_m3u8_formats(
            hls_url, video_id, ext='mp4', m3u8_id='hls'))
        self._remove_duplicate_formats(formats)

        uploader_url = traverse_obj(metadata, ('live', 'user', 'user_path'), expected_type=str)
        if uploader_url:
            uploader_url = f'https://whowatch.tv/profile/{uploader_url}'
        uploader_id = str(traverse_obj(metadata, ('live', 'user', 'id'), expected_type=int))
        uploader = traverse_obj(metadata, ('live', 'user', 'name'), expected_type=str)
        thumbnail = traverse_obj(metadata, ('live', 'latest_thumbnail_url'), expected_type=str)
        timestamp = int_or_none(traverse_obj(metadata, ('live', 'started_at'), expected_type=int), scale=1000)
        view_count = traverse_obj(metadata, ('live', 'total_view_count'), expected_type=int)
        comment_count = traverse_obj(metadata, ('live', 'comment_count'), expected_type=int)

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
