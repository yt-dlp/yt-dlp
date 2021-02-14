# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unified_timestamp,
)


class CamTubeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|api)\.)?camtube\.co/recordings?/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://camtube.co/recording/minafay-030618-1136-chaturbate-female',
        'info_dict': {
            'id': '42ad3956-dd5b-445a-8313-803ea6079fac',
            'display_id': 'minafay-030618-1136-chaturbate-female',
            'ext': 'mp4',
            'title': 'minafay-030618-1136-chaturbate-female',
            'duration': 1274,
            'timestamp': 1528018608,
            'upload_date': '20180603',
            'age_limit': 18
        },
        'params': {
            'skip_download': True,
        },
    }]

    _API_BASE = 'https://api.camtube.co'

    def _real_extract(self, url):
        display_id = self._match_id(url)

        token = self._download_json(
            '%s/rpc/session/new' % self._API_BASE, display_id,
            'Downloading session token')['token']

        self._set_cookie('api.camtube.co', 'session', token)

        video = self._download_json(
            '%s/recordings/%s' % (self._API_BASE, display_id), display_id,
            headers={'Referer': url})

        video_id = video['uuid']
        timestamp = unified_timestamp(video.get('createdAt'))
        duration = int_or_none(video.get('duration'))
        view_count = int_or_none(video.get('viewCount'))
        like_count = int_or_none(video.get('likeCount'))
        creator = video.get('stageName')

        formats = [{
            'url': '%s/recordings/%s/manifest.m3u8'
                   % (self._API_BASE, video_id),
            'format_id': 'hls',
            'ext': 'mp4',
            'protocol': 'm3u8_native',
        }]

        return {
            'id': video_id,
            'display_id': display_id,
            'title': display_id,
            'timestamp': timestamp,
            'duration': duration,
            'view_count': view_count,
            'like_count': like_count,
            'creator': creator,
            'formats': formats,
            'age_limit': 18
        }
