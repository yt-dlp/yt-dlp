# coding: utf-8
from __future__ import unicode_literals

import re

from .youtube import YoutubeIE
from .common import InfoExtractor
from ..utils import (
    unified_timestamp,
    extract_attributes,
)


class N1InfoAssetIE(InfoExtractor):
    _VALID_URL = r'https?://best-vod\.umn\.cdn\.united\.cloud/stream\?asset=(?P<id>[^&]+)'
    _TESTS = [{
        'url': 'https://best-vod.umn.cdn.united.cloud/stream?asset=ljsottomazilirija3060921-n1info-si-worldwide&stream=hp1400&t=0&player=m3u8v&sp=n1info&u=n1info&p=n1Sh4redSecre7iNf0',
        'md5': '28b08b32aeaff2b8562736ccd5a66fe7',
        'info_dict': {
            'id': 'ljsottomazilirija3060921-n1info-si-worldwide',
            'ext': 'mp4',
            'title': 'ljsottomazilirija3060921-n1info-si-worldwide',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats = self._extract_m3u8_formats(
            url, video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats
        }


class N1InfoIIE(InfoExtractor):
    IE_NAME = 'N1info:article'
    _VALID_URL = r'https?://(?:(?:ba|rs|hr)\.)?n1info\.(?:com|si)/[^/]+/(?:[^/]+/)?(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://rs.n1info.com/sport-klub/tenis/kako-je-djokovic-propustio-istorijsku-priliku-video/',
        'md5': '01ddb6646d0fd9c4c7d990aa77fe1c5a',
        'info_dict': {
            'id': 'L5Hd4hQVUpk',
            'ext': 'mp4',
            'upload_date': '20210913',
            'title': 'Ozmo i USO21, ep. 13: Novak Đoković – Danil Medvedev | Ključevi Poraza, Budućnost | SPORT KLUB TENIS',
            'description': 'md5:467f330af1effedd2e290f10dc31bb8e',
            'uploader': 'Sport Klub',
            'uploader_id': 'sportklub',
        }
    }, {'url': 'https://rs.n1info.com/vesti/djilas-los-plan-za-metro-nece-resiti-nijedan-saobracajni-problem/',
        'info_dict': {
            'id': 'bgmetrosot2409zta20210924174316682-n1info-rs-worldwide',
            'ext': 'mp4',
            'title': 'bgmetrosot2409zta20210924174316682-n1info-rs-worldwide'
        }},
        {'url': 'https://n1info.si/novice/slovenija/zadnji-dnevi-na-kopaliscu-ilirija-ilirija-ni-umrla-ubili-so-jo/',
         'info_dict': {
             'id': 'ljsottomazilirija3060921-n1info-si-worldwide',
             'ext': 'mp4',
             'title': 'ljsottomazilirija3060921-n1info-si-worldwide'
         }
         }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<h1[^>]+>(.+?)</h1>', webpage, 'title')
        timestamp = unified_timestamp(self._html_search_meta('article:published_time', webpage))

        videos = re.findall(r'(?m)(<video[^>]+>)', webpage)
        entries = []
        for video in videos:
            video_data = extract_attributes(video)
            entries.append(
                self.url_result(
                    video_data.get('data-url'),
                    ie=N1InfoAssetIE.ie_key(),
                    video_id=video_data.get('id'), video_title=title))

        youtube_videos = re.findall(r'(<iframe[^>]+>)', webpage)
        for youtube_video in youtube_videos:
            video_data = extract_attributes(youtube_video)
            url = video_data.get('src')
            if url.startswith('https://www.youtube.com'):
                entries.append(self.url_result(url, ie=YoutubeIE.ie_key()))

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': title,
            'timestamp': timestamp,
            'entries': entries,
            'ie_key': N1InfoAssetIE.ie_key(),
        }
