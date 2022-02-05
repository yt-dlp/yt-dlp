# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    clean_html,
    dict_get,
    try_get,
    unified_strdate,
)


class CanalAlphaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?canalalpha\.ch/play/[^/]+/[^/]+/(?P<id>\d+)/?.*'

    _TESTS = [{
        'url': 'https://www.canalalpha.ch/play/le-journal/episode/24520/jeudi-28-octobre-2021',
        'info_dict': {
            'id': '24520',
            'ext': 'mp4',
            'title': 'Jeudi 28 octobre 2021',
            'description': 'md5:d30c6c3e53f8ad40d405379601973b30',
            'thumbnail': 'https://static.canalalpha.ch/poster/journal/journal_20211028.jpg',
            'upload_date': '20211028',
            'duration': 1125,
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.canalalpha.ch/play/le-journal/topic/24512/la-poste-fait-de-neuchatel-un-pole-cryptographique',
        'info_dict': {
            'id': '24512',
            'ext': 'mp4',
            'title': 'La Poste fait de Neuchâtel un pôle cryptographique',
            'description': 'md5:4ba63ae78a0974d1a53d6703b6e1dedf',
            'thumbnail': 'https://static.canalalpha.ch/poster/news/news_39712.jpg',
            'upload_date': '20211028',
            'duration': 138,
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.canalalpha.ch/play/eureka/episode/24484/ces-innovations-qui-veulent-rendre-lagriculture-plus-durable',
        'info_dict': {
            'id': '24484',
            'ext': 'mp4',
            'title': 'Ces innovations qui veulent rendre l’agriculture plus durable',
            'description': 'md5:3de3f151180684621e85be7c10e4e613',
            'thumbnail': 'https://static.canalalpha.ch/poster/magazine/magazine_10236.jpg',
            'upload_date': '20211026',
            'duration': 360,
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.canalalpha.ch/play/avec-le-temps/episode/23516/redonner-de-leclat-grace-au-polissage',
        'info_dict': {
            'id': '23516',
            'ext': 'mp4',
            'title': 'Redonner de l\'éclat grâce au polissage',
            'description': 'md5:0d8fbcda1a5a4d6f6daa3165402177e1',
            'thumbnail': 'https://static.canalalpha.ch/poster/magazine/magazine_9990.png',
            'upload_date': '20210726',
            'duration': 360,
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        data_json = self._parse_json(self._search_regex(
            r'window\.__SERVER_STATE__\s?=\s?({(?:(?!};)[^"]|"([^"]|\\")*")+})\s?;',
            webpage, 'data_json'), id)['1']['data']['data']
        manifests = try_get(data_json, lambda x: x['video']['manifests'], expected_type=dict) or {}
        subtitles = {}
        formats = [{
            'url': video['$url'],
            'ext': 'mp4',
            'width': try_get(video, lambda x: x['res']['width'], expected_type=int),
            'height': try_get(video, lambda x: x['res']['height'], expected_type=int),
        } for video in try_get(data_json, lambda x: x['video']['mp4'], expected_type=list) or [] if video.get('$url')]
        if manifests.get('hls'):
            m3u8_frmts, m3u8_subs = self._parse_m3u8_formats_and_subtitles(manifests['hls'], video_id=id)
            formats.extend(m3u8_frmts)
            subtitles = self._merge_subtitles(subtitles, m3u8_subs)
        if manifests.get('dash'):
            dash_frmts, dash_subs = self._parse_mpd_formats_and_subtitles(manifests['dash'])
            formats.extend(dash_frmts)
            subtitles = self._merge_subtitles(subtitles, dash_subs)
        self._sort_formats(formats)
        return {
            'id': id,
            'title': data_json.get('title').strip(),
            'description': clean_html(dict_get(data_json, ('longDesc', 'shortDesc'))),
            'thumbnail': data_json.get('poster'),
            'upload_date': unified_strdate(dict_get(data_json, ('webPublishAt', 'featuredAt', 'diffusionDate'))),
            'duration': try_get(data_json, lambda x: x['video']['duration'], expected_type=int),
            'formats': formats,
            'subtitles': subtitles,
        }
