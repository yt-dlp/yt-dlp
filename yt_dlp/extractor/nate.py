# coding: utf-8
from __future__ import unicode_literals

import itertools

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
            'channel_id': '3606',
            'uploader_id': '3606',
            'tags': 'count:59',
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
            'channel_id': '27987',
            'uploader_id': '27987',
            'tags': 'count:20',
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
            'channel_id': str(video_data.get('programSeq')),
            'uploader_id': str(video_data.get('programSeq')),
            'tags': video_data['hashTag'].split(',') if video_data.get('hashTag') else None,
        }


class NateProgramIE(InfoExtractor):
    _VALID_URL = r'https?://tv\.nate\.com/program/clips/(?P<id>[0-9]+)'

    _TESTS = [{
        'url': 'https://tv.nate.com/program/clips/27987',
        'playlist_mincount': 191,
        'info_dict': {
            'id': '27987',
        },
    }, {
        'url': 'https://tv.nate.com/program/clips/3606',
        'playlist_mincount': 15,
        'info_dict': {
            'id': '3606',
        },
    }]

    def _entries(self, id):
        for page_num in itertools.count(1):
            program_data = self._download_json(f'https://tv.nate.com/api/v1/program/{id}/clip/ranking?size=20&page={page_num}',
                                               id, note=f'Downloading page {page_num}')
            for clip in program_data.get('content') or []:
                clip_id = clip.get('clipSeq')
                if clip_id:
                    yield self.url_result(
                        'https://tv.nate.com/clip/%s' % clip_id,
                        ie=NateIE.ie_key(), video_id=clip_id)
            if program_data.get('last'):
                break

    def _real_extract(self, url):
        id = self._match_id(url)
        return self.playlist_result(self._entries(id), playlist_id=id)
