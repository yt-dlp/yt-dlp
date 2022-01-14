# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    parse_qs,
    smuggle_url,
    unescapeHTML,
    unsmuggle_url,
)


class ErtGrWebtvEmbedIE(InfoExtractor):
    IE_NAME = 'ertgrwebtv:embed'
    IE_DESC = 'ert.gr webtv embedded videos'
    _BASE_PLAYER_URL_RE = re.escape('//www.ert.gr/webtv/live-uni/vod/dt-uni-vod.php')
    _VALID_URL = rf'https?:{_BASE_PLAYER_URL_RE}\?([^#]+&)?f=(?P<id>[^#&]+)'

    _TESTS = [{
        'url': 'https://www.ert.gr/webtv/live-uni/vod/dt-uni-vod.php?f=trailers/E2251_TO_DIKTYO_E09_16-01_1900.mp4&bgimg=/photos/2022/1/to_diktio_ep09_i_istoria_tou_diadiktiou_stin_Ellada_1021x576.jpg',
        'md5': 'f9e9900c25c26f4ecfbddbb4b6305854',
        'info_dict': {
            'id': 'trailers/E2251_TO_DIKTYO_E09_16-01_1900.mp4',
            'title': 'md5:914f06a73cd8b62fbcd6fb90c636e497',
            'ext': 'mp4',
            'thumbnail': 'https://program.ert.gr/photos/2022/1/to_diktio_ep09_i_istoria_tou_diadiktiou_stin_Ellada_1021x576.jpg'
        },
    }]

    @staticmethod
    def _smuggle_parent_info(url, **info_dict):
        return smuggle_url(url, {'parent_info': info_dict})

    @staticmethod
    def _unsmuggle_parent_info(url):
        unsmuggled_url, data = unsmuggle_url(url, default={'parent_info': {}})
        return unsmuggled_url, data['parent_info']

    @classmethod
    def _extract_urls(cls, webpage, **parent_info):
        # in comparison with _VALID_URL:
        # * make the scheme optional
        # * simplify the query string part; after extracting iframe src, the URL will be matched again
        VALID_SRC = rf'(?:https?:)?{cls._BASE_PLAYER_URL_RE}\?(?:(?!(?P=_q1)).)+'

        EMBED_RE = r'''<iframe[^>]+?src=(?P<_q1>["'])(?P<url>%s)(?P=_q1)''' % VALID_SRC

        for mobj in re.finditer(EMBED_RE, webpage):
            url = unescapeHTML(mobj.group('url'))
            if not cls.suitable(url):
                continue
            yield cls._smuggle_parent_info(url, **parent_info)

    def _real_extract(self, url):
        url, parent_info = type(self)._unsmuggle_parent_info(url)
        video_id = self._match_id(url)
        thumbnail_id = parse_qs(url).get('bgimg', [None])[0]
        format_url = f'https://mediastream.ert.gr/vodedge/_definst_/mp4:dvrorigin/{video_id}/playlist.m3u8'
        formats, subs = self._extract_m3u8_formats_and_subtitles(
            format_url, video_id, 'mp4')
        self._sort_formats(formats)
        thumbnail_url = f'https://program.ert.gr{thumbnail_id}' if thumbnail_id else None
        return {
            'id': video_id,
            'title': parent_info.get('title') or f'VOD - {video_id}',
            'thumbnail': thumbnail_url,
            'formats': formats,
            'subtitles': subs,
        }
