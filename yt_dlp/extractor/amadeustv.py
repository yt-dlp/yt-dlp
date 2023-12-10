from .common import InfoExtractor
from ..utils import (
    int_or_none,
    ExtractorError,
    traverse_obj,
    parse_codecs,
)

class AmadeusTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?amadeus\.tv/library/(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'http://www.amadeus.tv/library/65091a87ff85af59d9fc54c3',
        'info_dict': {
            'id': '5576678021301411311',
            'ext': 'mp4',
            'title': '02Jieon Park.mp4',
            'thumbnail': 'http://1253584441.vod2.myqcloud.com/a0046a27vodtransbj1253584441/7db4af535576678021301411311/coverBySnapshot_10_0.jpg',
            'duration': 1264,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        nuxt_data = self._search_nuxt_data(webpage, video_id, traverse=('fetch', '0'))
        actual_video_id = traverse_obj(nuxt_data, ('item', 'video'))

        if not actual_video_id:
            raise ExtractorError('Unable to extract actual video ID')

        video_data = self._download_json(
            f'http://playvideo.qcloud.com/getplayinfo/v2/1253584441/{actual_video_id}',
            actual_video_id,
            headers={'Referer': 'http://www.amadeus.tv/'}
        )

        transcode_list = traverse_obj(video_data, ('videoInfo', 'transcodeList'), default=[])
        formats = []
        for video in transcode_list:
            format_info = {
                'url': video['url'],
                'format_id': 'http-%d' % video['definition'],
                'width': int_or_none(video.get('width')),
                'height': int_or_none(video.get('height')),
                'filesize': int_or_none(video.get('size')),
                'vcodec': video.get('videoStreamList', [{}])[0].get('codec'),
                'acodec': video.get('audioStreamList', [{}])[0].get('codec'),
                'fps': int_or_none(video.get('videoStreamList', [{}])[0].get('fps')),
                'http_headers': {'Referer': 'http://www.amadeus.tv/'}
            }
            formats.append(format_info)

        return {
            'id': actual_video_id,
            'title': traverse_obj(video_data, ('videoInfo', 'basicInfo', 'name'), default=video_id),
            'thumbnail': traverse_obj(video_data, ('coverInfo', 'coverUrl')),
            'formats': formats,
            'duration': int_or_none(traverse_obj(video_data, ('videoInfo', 'sourceVideo', 'duration'))),
        }
