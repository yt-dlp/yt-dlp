import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unified_strdate,
)


class MBNIE(InfoExtractor):
    IE_DESC = 'mbn.co.kr (매일방송)'
    _VALID_URL = r'https?://(?:www\.)?mbn\.co\.kr/vod/programContents/(?:previewlist|preview)/[0-9]+/[0-9]+/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://mbn.co.kr/vod/programContents/previewlist/861/5433/1276155',
        'md5': '85e1694e5b247c04d1386b7e3c90fd76',
        'info_dict': {
            'id': '1276155',
            'ext': 'mp4',
            'title': '결국 사로잡힌 권유리, 그녀를 목숨 걸고 구하려는 정일우!',
            'duration': 3891,
            'release_date': '20210703',
            'thumbnail': 'http://img.vod.mbn.co.kr/mbnvod2img/861/2021/07/03/20210703230811_20_861_1276155_360_7_0.jpg',
            'series': '보쌈 - 운명을 훔치다',
            'episode': 'Episode 19',
            'episode_number': 19,
        },
    }, {
        'url': 'https://www.mbn.co.kr/vod/programContents/previewlist/835/5294/1084744',
        'md5': 'fc65d3aac85e85e0b5056f4ef99cde4a',
        'info_dict': {
            'id': '1084744',
            'ext': 'mp4',
            'title': '김정은♥최원영, 제자리를 찾은 위험한 부부! ＂결혼은 투쟁이면서, 어려운 방식이야..＂',
            'duration': 93,
            'release_date': '20201124',
            'thumbnail': 'http://img.vod.mbn.co.kr/mbnvod2img/835/2020/11/25/20201125000221_21_835_1084744_360_7_0.jpg',
            'series': '나의 위험한 아내',
        },
    }, {
        'url': 'https://www.mbn.co.kr/vod/programContents/preview/952/6088/1054797?next=1',
        'md5': 'c711103c72aeac8323a5cf1751f10097',
        'info_dict': {
            'id': '1054797',
            'ext': 'mp4',
            'title': '[2차 티저] MBN 주말 미니시리즈 <완벽한 결혼의 정석> l 그녀에게 주어진 두 번째 인생',
            'duration': 65,
            'release_date': '20231028',
            'thumbnail': 'http://img.vod.mbn.co.kr/vod2/952/2023/09/11/20230911130223_22_952_1054797_1080_7.jpg',
            'series': '완벽한 결혼의 정석',
        },
    }]

    def _real_extract(self, url):
        content_id = self._match_id(url)
        webpage = self._download_webpage(url, content_id)

        content_cls_cd = self._search_regex(r'"\?content_cls_cd=(\d+)&', webpage, 'content_cls_cd', default='20')
        media_info = self._download_json(
            f'https://www.mbn.co.kr/player/mbnVodPlayer_2020.mbn?content_cls_cd={content_cls_cd}&content_id={content_id}&relay_type=1',
            content_id, note='Fetching playback data')

        formats = []
        for stream in media_info.get('movie_list'):
            if not stream.get('url'):
                continue
            location = re.sub(r'/(?:chunklist|playlist)(?:_pd180000)?\.m3u8', '/manifest.m3u8', stream['url'])
            m3u8_url = self._download_webpage(
                f'https://www.mbn.co.kr/player/mbnStreamAuth_new_vod.mbn?vod_url={location}',
                content_id, note='Generating authenticated m3u8 url')

            formats.extend(self._extract_m3u8_formats(m3u8_url, content_id))

        return {
            'id': content_id,
            'title': media_info.get('movie_title'),
            'duration': int_or_none(media_info.get('play_sec')),
            'release_date': unified_strdate(media_info.get('bcast_date').replace('.', '')),
            'thumbnail': media_info.get('movie_start_Img'),
            'series': media_info.get('prog_nm'),
            'episode_number': int_or_none(media_info.get('ad_contentnumber')),
            'formats': formats,
        }
