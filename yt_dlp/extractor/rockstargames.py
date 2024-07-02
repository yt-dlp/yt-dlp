from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
)


class RockstarGamesIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?rockstargames\.com/videos(?:/video/|#?/?\?.*\bvideo=)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.rockstargames.com/videos/video/11544/',
        'md5': '03b5caa6e357a4bd50e3143fc03e5733',
        'info_dict': {
            'id': '11544',
            'ext': 'mp4',
            'title': 'Further Adventures in Finance and Felony Trailer',
            'description': 'md5:6d31f55f30cb101b5476c4a379e324a3',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1464876000,
            'upload_date': '20160602',
        },
    }, {
        'url': 'http://www.rockstargames.com/videos#/?video=48',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'https://www.rockstargames.com/videoplayer/videos/get-video.json',
            video_id, query={
                'id': video_id,
                'locale': 'en_us',
            })['video']

        title = video['title']

        formats = []
        for v in video['files_processed']['video/mp4']:
            if not v.get('src'):
                continue
            resolution = v.get('resolution')
            height = int_or_none(self._search_regex(
                r'^(\d+)[pP]$', resolution or '', 'height', default=None))
            formats.append({
                'url': self._proto_relative_url(v['src']),
                'format_id': resolution,
                'height': height,
            })

        if not formats:
            youtube_id = video.get('youtube_id')
            if youtube_id:
                return self.url_result(youtube_id, 'Youtube')

        return {
            'id': video_id,
            'title': title,
            'description': video.get('description'),
            'thumbnail': self._proto_relative_url(video.get('screencap')),
            'timestamp': parse_iso8601(video.get('created')),
            'formats': formats,
        }
