from .common import InfoExtractor
from ..utils import traverse_obj, unified_strdate


class MatchiTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?matchi\.tv/watch\?s=(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://matchi.tv/watch?s=0euhjzrxsjm',
        'info_dict': {
            'id': '0euhjzrxsjm',
            'ext': 'mp4',
            'title': 'Court 2 at Stratford Padel Club 2024-07-13T18:32:24',
            'thumbnail': 'https://thumbnails.padelgo.tv/0euhjzrxsjm.jpg',
            'upload_date': '20240713',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # Extract JSON data from __NEXT_DATA__ script tag
        page_data = self._search_json(
            r'<script[^>]+id="__NEXT_DATA__"[^>]*>', webpage, 'next data', video_id, fatal=False)

        loaded_media = traverse_obj(page_data, ('props', 'pageProps', 'loadedMedia'), default={})
        court_description = traverse_obj(loaded_media, 'courtDescription')
        start_date_time = traverse_obj(loaded_media, 'startDateTime')

        return {
            'id': video_id,
            'title': f'{court_description} {start_date_time}',
            'thumbnail': f'https://thumbnails.padelgo.tv/{video_id}.jpg',
            'upload_date': unified_strdate(start_date_time),
            'formats': self._extract_m3u8_formats(
                f'https://streams.padelgo.tv/v2/streams/m3u8/{video_id}/anonymous/playlist.m3u8',
                video_id,
                'mp4',
                entry_protocol='m3u8_native',
                m3u8_id='hls',
                fatal=False),
        }
