# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    int_or_none,
    try_get,
    unified_timestamp,
)


class FreshLiveIE(InfoExtractor):
    _VALID_URL = r'https?://freshlive\.tv/[^/]+/(?P<id>\d+)'
    _TEST = {
        'url': 'https://freshlive.tv/satotv/74712',
        'md5': '9f0cf5516979c4454ce982df3d97f352',
        'info_dict': {
            'id': '74712',
            'ext': 'mp4',
            'title': 'テスト',
            'description': 'テスト',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1511,
            'timestamp': 1483619655,
            'upload_date': '20170105',
            'uploader': 'サトTV',
            'uploader_id': 'satotv',
            'view_count': int,
            'comment_count': int,
            'is_live': False,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        options = self._parse_json(
            self._search_regex(
                r'window\.__CONTEXT__\s*=\s*({.+?});\s*</script>',
                webpage, 'initial context'),
            video_id)

        info = options['context']['dispatcher']['stores']['ProgramStore']['programs'][video_id]

        title = info['title']

        if info.get('status') == 'upcoming':
            raise ExtractorError('Stream %s is upcoming' % video_id, expected=True)

        stream_url = info.get('liveStreamUrl') or info['archiveStreamUrl']

        is_live = info.get('liveStreamUrl') is not None

        formats = self._extract_m3u8_formats(
            stream_url, video_id, 'mp4',
            'm3u8_native', m3u8_id='hls')

        if is_live:
            title = self._live_title(title)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': info.get('description'),
            'thumbnail': info.get('thumbnailUrl'),
            'duration': int_or_none(info.get('airTime')),
            'timestamp': unified_timestamp(info.get('createdAt')),
            'uploader': try_get(
                info, lambda x: x['channel']['title'], compat_str),
            'uploader_id': try_get(
                info, lambda x: x['channel']['code'], compat_str),
            'uploader_url': try_get(
                info, lambda x: x['channel']['permalink'], compat_str),
            'view_count': int_or_none(info.get('viewCount')),
            'comment_count': int_or_none(info.get('commentCount')),
            'tags': info.get('tags', []),
            'is_live': is_live,
        }
