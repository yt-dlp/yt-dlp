# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor

from ..utils import (
    js_to_json,
    try_get,
    int_or_none,
    str_or_none,
    url_or_none,
)
from ..compat import compat_str


class TrovoLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?trovo\.live/video/(?P<id>[\w-]+)'
    _TEST = {
        'url': 'https://trovo.live/video/ltv-100759829_100759829_1610625308',
        'md5': 'ea7b58427910e9af66a462d895201a30',
        'info_dict': {
            'id': 'ltv-100759829_100759829_1610625308',
            'ext': 'ts',
            'title': 'GTA RP ASTERIX doa najjaca',
            'uploader': 'Peroo42',
            'duration': 5872,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'categories': list,
            'is_live': False,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader_id': '100759829',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        nuxt = self._search_regex(r'\bwindow\.__NUXT__\s*=\s*(.+?);?\s*</script>', webpage, 'nuxt', default='')
        mobj = re.search(r'\((?P<arg_names>[^(]+)\)\s*{\s*return\s+(?P<json>{.+})\s*\((?P<args>.+?)\)\s*\)$', nuxt)

        vod_details = vod_info = {}
        if mobj:
            vod_details = self._parse_json(
                js_to_json(
                    self._search_regex(r'VodDetailInfos\s*:({.+?}),\s*_', webpage, 'VodDetailInfos'),
                    dict(zip(
                        (i.strip() for i in mobj.group('arg_names').split(',')),
                        (i.strip() for i in mobj.group('args').split(','))))),
                video_id)
            vod_info = try_get(vod_details, lambda x: x['json'][video_id]['vodInfo'], dict) or {}

        player_info = self._parse_json(
            self._search_regex(
                r'_playerInfo\s*=\s*({.+?})\s*</script>', webpage, 'player info'),
            video_id)

        title = (
            vod_info.get('title')
            or self._html_search_regex(r'<h3>(.+?)</h3>', webpage, 'title', fatal=False)
            or self._og_search_title(webpage))
        uploader = (
            try_get(vod_details, lambda x: x['json'][video_id]['streamerInfo']['userName'], compat_str)
            or self._search_regex(r'<div[^>]+userName\s=\s[\'"](.+?)[\'"]', webpage, 'uploader', fatal=False))

        format_dicts = vod_info.get('playInfos') or player_info.get('urlArray') or []

        def _extract_format_data(format_dict):
            res = format_dict.get('desc')
            enc = str_or_none(format_dict.get('encodeType'))
            if enc:
                notes = [enc.replace('VOD_ENCODE_TYPE_', '')]
            level = str_or_none(format_dict.get('levelType'))
            if level:
                notes.append('level %s' % level)
            height = int_or_none(res[:-1]) if res else None
            bitrate = format_dict.get('bitrate')
            fid = res or ('%sk' % str_or_none(bitrate) if bitrate else None) or ' '.join(notes)

            return {
                'url': format_dict['playUrl'],
                'format_id': fid,
                'format_note': ' '.join(notes),
                'height': height,
                'resolution': str_or_none(res),
                'tbr': int_or_none(bitrate),
                'filesize': int_or_none(format_dict.get('fileSize')),
                'vcodec': 'avc3',
                'acodec': 'aac',
                'ext': 'ts'
            }

        formats = [_extract_format_data(f) for f in format_dicts]
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'duration': int_or_none(vod_info.get('duration')),
            'formats': formats,
            'view_count': int_or_none(vod_info.get('watchNum')),
            'like_count': int_or_none(vod_info.get('likeNum')),
            'comment_count': int_or_none(vod_info.get('commentNum')),
            'categories': [str_or_none(vod_info.get('categoryName'))],
            'is_live': try_get(player_info, lambda x: x['isLive'], bool),
            'thumbnail': url_or_none(vod_info.get('coverUrl')),
            'uploader_id': str_or_none(try_get(vod_details, lambda x: x['json'][video_id]['streamerInfo']['uid'])),
        }
