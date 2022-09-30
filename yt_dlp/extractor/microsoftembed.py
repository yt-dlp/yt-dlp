from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    unified_timestamp,
    int_or_none,
)


class MicrosoftEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?microsoft\.com/(?:[^/]+/)?videoplayer/embed/(?P<id>[a-z0-9A-Z]+)'

    _TESTS = [{
        'url': 'https://www.microsoft.com/en-us/videoplayer/embed/RWL07e',
        'md5': 'eb0ae9007f9b305f9acd0a03e74cb1a9',
        'info_dict': {
            'id': 'RWL07e',
            'title': 'Microsoft for Public Health and Social Services',
            'ext': 'mp4',
            'thumbnail': 'http://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWL7Ju?ver=cae5',
            'age_limit': 0,
            'timestamp': 1631658316,
            'upload_date': '20210914'
        }
    }]
    _API_URL = 'https://prod-video-cms-rt-microsoft-com.akamaized.net/vhs/api/videos/'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._download_json(self._API_URL + video_id, video_id)
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

        subtitles = {
            lang: [{
                'url': data.get('url'),
                'ext': 'vtt'
            }] for lang, data in traverse_obj(metadata, 'captions', default={}).items()
        }

        thumbnails = traverse_obj(metadata, ('snippet', 'thumbnails', ..., {
            'url': 'url',
            'width': 'width',
            'height': 'height'
        }))

        return {
            'id': video_id,
            'title': traverse_obj(metadata, ('snippet', 'title')),
            'thumbnails': thumbnails,
            'timestamp': unified_timestamp(traverse_obj(metadata, ('snippet', 'activeStartDate'))),
            'formats': formats,
            'age_limit': int_or_none(traverse_obj(metadata, ('snippet', 'minimumAge'))) or 0,
            'subtitles': subtitles
        }
