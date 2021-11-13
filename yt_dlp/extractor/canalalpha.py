# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    clean_html,
    try_get,
    unified_strdate,
)


class CanalAlphaIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?canalalpha\.ch/play/[^/]+/[^/]+/(?P<id>\d+)/?.*'

    _TESTS = []

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        data_json = self._parse_json(self._html_search_regex(r'window\.__SERVER_STATE__\s?=\s?({.*});', webpage, 'data_json'),id)['1']['data']['data']
        manifests = try_get(data_json, lambda x: x['video']['manifests'], expected_type=dict) or {}
        formats, subtitles = [], {}
        if manifests.get('hls'):
            m3u8_frmts, m3u8_subs = self._parse_m3u8_formats_and_subtitles(manifests['hls'], id)
            formats.extend(m3u8_frmts)
            subtitles = self._merge_subtitles(subtitles, m3u8_subs)
        if manifests.get('dash'):
            dash_frmts, dash_subs = self._parse_mpd_formats_and_subtitles(manifests['dash'], id)
            formats.extend(dash_frmts)
            subtitles = self._merge_subtitles(subtitles, dash_subs)
        for video in try_get(data_json, lambda x: x['video']['mp4'], expected_type=list) or []:
            video_url = video.get('$url')
            if video_url:
                formats.append({
                    'url': video_url,
                    'ext': 'mp4',
                    'width': try_get(video, lambda x: x['res']['width'], expected_type=int),
                    'height': try_get(video, lambda x: x['res']['height'], expected_type=int),
                })
        self._sort_formats(formats)
        return {
            'id': id,
            'title': data_json.get('title'),
            'description': clean_html(data_json.get('longDesc') or data_json.get('shortDesc')),
            'thumbnail': data_json.get('poster'),
            'upload_date': unified_strdate(data_json.get('webPublishAt') or data_json.get('featuredAt') or data_json.get('diffusionDate')),
            'formats': formats,
            'subtitles': subtitles,
        }
