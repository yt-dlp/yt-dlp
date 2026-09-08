from .common import InfoExtractor
from ..utils import join_nonempty, unified_strdate
from ..utils.traversal import traverse_obj


class MatchiTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?matchi\.tv/watch/?\?(?:[^#]+&)?s=(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://matchi.tv/watch?s=0euhjzrxsjm',
        'info_dict': {
            'id': '0euhjzrxsjm',
            'ext': 'mp4',
            'title': 'Court 2 at Stratford Padel Club 2024-07-13T18:32:24',
            'thumbnail': 'https://thumbnails.padelgo.tv/0euhjzrxsjm.jpg',
            'upload_date': '20240713',
        },
    }, {
        'url': 'https://matchi.tv/watch?s=FkKDJ9SvAx1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        loaded_media = traverse_obj(
            self._search_nextjs_data(webpage, video_id, fatal=False),
            ('props', 'pageProps', 'loadedMedia', {dict})) or {}
        start_date_time = traverse_obj(loaded_media, ('startDateTime', {str}))

        return {
            'id': video_id,
            'title': join_nonempty(loaded_media.get('courtDescription'), start_date_time, delim=' '),
            'thumbnail': f'https://thumbnails.padelgo.tv/{video_id}.jpg',
            'upload_date': unified_strdate(start_date_time),
            'formats': self._extract_m3u8_formats(
                f'https://streams.padelgo.tv/v2/streams/m3u8/{video_id}/anonymous/playlist.m3u8',
                video_id, 'mp4', m3u8_id='hls'),
        }
