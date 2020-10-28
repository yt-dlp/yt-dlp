# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import unified_timestamp
import re


class URPlayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ur(?:play|skola)\.se/(?:program|Produkter)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://urplay.se/program/203704-ur-samtiden-livet-universum-och-rymdens-markliga-musik-om-vetenskap-kritiskt-tankande-och-motstand',
        'md5': 'ff5b0c89928f8083c74bbd5099c9292d',
        'info_dict': {
            'id': '203704',
            'ext': 'mp4',
            'title': 'Om vetenskap, kritiskt tänkande och motstånd',
            'description': 'md5:5344508a52aa78c1ced6c1b8b9e44e9a',
            'timestamp': 1513292400,
            'upload_date': '20171214',
        },
    }, {
        'url': 'https://urskola.se/Produkter/190031-Tripp-Trapp-Trad-Sovkudde',
        'info_dict': {
            'id': '190031',
            'ext': 'mp4',
            'title': 'Tripp, Trapp, Träd : Sovkudde',
            'description': 'md5:b86bffdae04a7e9379d1d7e5947df1d1',
            'timestamp': 1440093600,
            'upload_date': '20150820',
        },
    }, {
        'url': 'http://urskola.se/Produkter/155794-Smasagor-meankieli-Grodan-i-vida-varlden',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        urplayer_data = re.sub("&quot;", "\"", self._search_regex(
            r'components\/Player\/Player\" data-react-props=\"({.+?})\"',
            webpage, 'urplayer data'))
        urplayer_data = self._parse_json(urplayer_data, video_id)
        for i in range(len(urplayer_data['accessibleEpisodes'])):
            if urplayer_data.get('accessibleEpisodes', {})[i].get('id') == int(video_id):
                urplayer_data = urplayer_data['accessibleEpisodes'][i]
                break

        host = self._download_json('http://streaming-loadbalancer.ur.se/loadbalancer.json', video_id)['redirect']
        formats = []
        urplayer_streams = urplayer_data.get("streamingInfo")
        for quality in ('sd'), ('hd'):
            location = (urplayer_streams.get("raw", {}).get(quality, {}).get("location")
                        or urplayer_streams.get("sweComplete", {}).get(quality, {}).get("location"))
            if location:
                formats.extend(self._extract_wowza_formats(
                               'http://%s/%s/playlist.m3u8' % (host, location), video_id,
                               skip_protocols=['f4m', 'rtmp', 'rtsp']))
        self._sort_formats(formats)
        subtitles = {}
        subs = urplayer_streams.get("sweComplete", {}).get("tt", {}).get("location")
        if subs:
            subtitles.setdefault('Svenska', []).append({
                'url': subs,
            })

        return {
            'id': video_id,
            'title': urplayer_data['title'],
            'description': self._og_search_description(webpage),
            'thumbnail': urplayer_data.get('image', {}).get('1280x720'),
            'timestamp': unified_timestamp(self._html_search_meta(('uploadDate', 'schema:uploadDate'),
                                           webpage, 'timestamp')),
            'series': urplayer_data.get('seriesTitle'),
            'subtitles': subtitles,
            'formats': formats,
        }
