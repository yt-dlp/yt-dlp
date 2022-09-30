from .common import InfoExtractor


class MicrosoftEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?microsoft\.com/en-us/videoplayer/embed/(?P<id>[a-z0-9A-Z]+)'
    _TESTS = [{
        'url': 'https://www.microsoft.com/en-us/videoplayer/embed/RWL07e',
        'only_matching': True
    }]
    _API_URL = 'https://prod-video-cms-rt-microsoft-com.akamaized.net/vhs/api/videos/'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        metadata = self._download_json(
            self._API_URL + video_id,
            video_id)

        formats = []
        streams = metadata['streams']

        for key, value in streams:
            stream_url = value['url']

            if key in ('smoothStreaming', 'apple_HTTP_Live_Streaming', 'mPEG_DASH'):
                formats.extend(self._extract_ism_formats((stream_url, video_id)))

            # else:
            #     formats[key] = value

        output = {
            'id': video_id,
            'title': metadata['snippet']['title'],
            'thumbnails': metadata['snippet']['thumbnails'],
            'timestamp': metadata['snippet']['activeStartDate'],
            'formats': formats
        }
        return output