from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    unified_timestamp,
    int_or_none,
)


class MicrosoftEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?microsoft\.com/en-us/videoplayer/embed/(?P<id>[a-z0-9A-Z]+)'

    _TESTS = [{
        'url': 'https://www.microsoft.com/en-us/videoplayer/embed/RWL07e',
        'info_dict': {
            'id': 'RWL07e',
            'title': '...'
        }
    }]
    _API_URL = 'https://prod-video-cms-rt-microsoft-com.akamaized.net/vhs/api/videos/'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        metadata = self._download_json(
            self._API_URL + video_id,
            video_id)

        formats = []
        for source_type, source in metadata['streams'].items():
            stream_url = source['url']

            if source_type == 'smoothStreaming':
                formats.extend(self._extract_ism_formats(stream_url, video_id, 'mss'))
            elif source_type == 'apple_HTTP_Live_Streaming':
                formats.extend(self._extract_m3u8_formats(stream_url, video_id))
            elif source_type == 'mPEG_DASH':
                formats.extend(self._extract_mpd_formats(stream_url, video_id))
            else:
                formats.append({
                    'format_id': source_type,
                    'url': stream_url,
                    'height': source.get('heightPixels'),
                    'width': source.get('widthPixels')
                })

        self._sort_formats(formats)

        timestamp = traverse_obj(
            metadata, ('snippet', 'activeStartDate'))

        age_limit = int_or_none(
            traverse_obj(metadata, ('snippet', 'minimumAge'))) or 0

        subtitles = {}

        for lang, data in (traverse_obj(metadata, 'captions') or {}).items():
            subtitles[lang] = [{
                'url': data.get('url'),
                'ext': 'vtt'
            }]

        thumbnails = []

        for thumbnail_size, data in (traverse_obj(metadata, ('snippet', 'thumbnails')) or {}).items():
            thumbnails.append({
                'url': data.get('url'),
                'http_headers': data.get('link')
            })

        return {
            'id': video_id,
            'title': traverse_obj(metadata, ('snippet', 'title')),
            'thumbnails': thumbnails,
            'timestamp': unified_timestamp(timestamp),
            'formats': formats,
            'age_limit': age_limit,
            'subtitles': subtitles
        }
