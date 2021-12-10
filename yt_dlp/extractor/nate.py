# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    unified_strdate,
)


class NateIE(InfoExtractor):
    _VALID_URL = r'https?://tv\.nate\.com/clip/(?P<id>[0-9]+)'

    _TESTS = [{
        'url': 'https://tv.nate.com/clip/1848976',
        'info_dict': {
            'id': '1848976',
            'ext': 'mp4',
            'title': '[결승 오프닝 타이틀] 2018 LCK 서머 스플릿 결승전 kt Rolster VS Griffin',
            'description': 'md5:e1b79a7dcf0d8d586443f11366f50e6f',
            'thumbnail': 'http://image.pip.cjenm.com/CLIP/GA/B120189687/B120189687_EPI0056_03_B.jpg',
            'upload_date': '20180908',
            'age_limit': 15,
            'duration': 73,
            'uploader': '2018 LCK 서머 스플릿(롤챔스)',
            'channel': '2018 LCK 서머 스플릿(롤챔스)',
            'channel_id': 3606,
            'uploader_id': 3606,
            'tags': ['#B120189687_c',
                     '#롤챔스',
                     '#Griffin결승',
                     '#kt결승',
                     '#롤챔스결승전',
                     '#서머결승전',
                     '#LoL결승전',
                     '#롤챔스서머',
                     '#롤챔스서머스플릿',
                     '#LCKSummer',
                     '#엘씨케이',
                     '#LCK',
                     '#2018LoLChampionsKoreaSummer',
                     '#KTRolster',
                     '#룰러',
                     '#Ruler',
                     '#데프트',
                     '#Deft',
                     '#김혁규',
                     '#알파카',
                     '#스멥',
                     '#송경호',
                     '#스맵',
                     '#마타',
                     '#mata',
                     '#리헨즈',
                     '#lehends',
                     '#score',
                     '#Ucal',
                     '#Viper',
                     '#바이퍼',
                     '#Sword',
                     '#Tazan',
                     '#Chovy',
                     '#페이Split',
                     '#LoL',
                     '#리그오브레전',
                     '#코동빈',
                     '#코동빈성불',
                     '#로얄로더',
                     '#LeagueofLegends',
                     '#esports',
                     '#이스포츠',
                     '#전용준',
                     '#김동준',
                     '#클템',
                     '#이현우',
                     '#클라우드템플러',
                     '#단군',
                     '#김의중',
                     '#용준좌',
                     '#동준좌',
                     '#페이커',
                     '#sktt1',
                     '#뱅',
                     '#배준식',
                     '#젠지',
                     '#킹존',
                     '#아프리카프릭스']
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://tv.nate.com/clip/4300566',
        'info_dict': {
            'id': '4300566',
            'ext': 'mp4',
            'title': '[심쿵엔딩] 이준호x이세영, 서로를 기억하며 끌어안는 두 사람!💕, MBC 211204 방송',
            'description': 'md5:be1653502d9c13ce344ddf7828e089fa',
            'thumbnail': 'http://d3gkeuh6j9q833.cloudfront.net/Attach/mbc/2021/12/04/TZ202112040078/clip_20211204231755_0.jpg',
            'upload_date': '20211204',
            'age_limit': 15,
            'duration': 201,
            'uploader': '옷소매 붉은 끝동',
            'channel': '옷소매 붉은 끝동',
            'channel_id': 27987,
            'uploader_id': 27987,
            'tags': ['이산',
                     '성덕임',
                     '홍덕로',
                     '영조',
                     '중전',
                     '드라마',
                     '사극',
                     'The Red Sleeve',
                     '옷소매 붉은 끝동',
                     '이준호',
                     '이세영',
                     '강훈',
                     '이덕화',
                     '박지영',
                     '장희진',
                     '장혜진',
                     '조희봉',
                     '서효림',
                     '강말금',
                     '오대환']
        },
        'params': {'skip_download': True}
    }]

    _QUALITY = {
        '36': '2160p',
        '35': '1080p',
        '34': '720p',
        '33': '480p',
        '32': '360p',
        '31': '270p',
    }

    def _real_extract(self, url):
        id = self._match_id(url)
        video_data = self._download_json(f'https://tv.nate.com/api/v1/clip/{id}', id)
        formats = [{
            'url': f_url,
            'resolution': self._QUALITY.get(f_url[-2:]),
        } for f_url in video_data.get('smcUriList') or []]
        return {
            'id': id,
            'title': video_data.get('clipTitle'),
            'description': video_data.get('synopsis'),
            'thumbnail': video_data.get('contentImg'),
            'upload_date': unified_strdate(traverse_obj(video_data, 'broadDate', 'regDate')),
            'age_limit': video_data.get('targetAge'),
            'duration': video_data.get('playTime'),
            'formats': formats,
            'uploader': video_data.get('programTitle'),
            'channel': video_data.get('programTitle'),
            'channel_id': video_data.get('programSeq'),
            'uploader_id': video_data.get('programSeq'),
            'tags': video_data['hashTag'].split(',') if video_data.get('hashTag') else None,
        }
