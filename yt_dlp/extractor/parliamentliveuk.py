# coding: utf-8
from __future__ import unicode_literals

import json
import uuid

from .common import InfoExtractor
from ..utils import (
    unified_timestamp,
    try_get,
)


class ParliamentLiveUKIE(InfoExtractor):
    IE_NAME = 'parliamentlive.tv'
    IE_DESC = 'UK parliament videos'
    _VALID_URL = r'(?i)https?://(?:www\.)?parliamentlive\.tv/Event/Index/(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'

    _TESTS = [{
        'url': 'http://parliamentlive.tv/Event/Index/c1e9d44d-fd6c-4263-b50f-97ed26cc998b',
        'info_dict': {
            'id': 'c1e9d44d-fd6c-4263-b50f-97ed26cc998b',
            'ext': 'mp4',
            'title': 'Home Affairs Committee',
            'timestamp': 1395153872,
            'upload_date': '20140318',
        },
    }, {
        'url': 'http://parliamentlive.tv/event/index/3f24936f-130f-40bf-9a5d-b3d6479da6a4',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._download_json(f'https://www.parliamentlive.tv/Event/GetShareVideo/{video_id}', video_id)
        _DEVICE_ID = str(uuid.uuid4())
        auth = 'Bearer ' + self._download_json(
            'https://exposure.api.redbee.live/v2/customer/UKParliament/businessunit/ParliamentLive/auth/anonymous',
            video_id, headers={
                'Origin': 'https://videoplayback.parliamentlive.tv',
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json;charset=utf-8'
            }, data=json.dumps({
                'deviceId': _DEVICE_ID,
                'device': {
                    'deviceId': _DEVICE_ID,
                    'width': 653,
                    'height': 368,
                    'type': 'WEB',
                    'name': ' Mozilla Firefox 91'
                }
            }).encode('utf-8'))['sessionToken']

        video_urls = self._download_json(
            f'https://exposure.api.redbee.live/v2/customer/UKParliament/businessunit/ParliamentLive/entitlement/{video_id}/play',
            video_id, headers={'Authorization': auth, 'Accept': 'application/json, text/plain, */*'})['formats']

        formats = []
        for format in video_urls:
            if not format.get('mediaLocator'):
                continue
            if format.get('format') == 'DASH':
                formats.extend(self._extract_mpd_formats(
                    format['mediaLocator'], video_id, mpd_id='dash', fatal=False))
            elif format.get('format') == 'SMOOTHSTREAMING':
                formats.extend(self._extract_ism_formats(
                    format['mediaLocator'], video_id, ism_id='ism', fatal=False))
            elif format.get('format') == 'HLS':
                formats.extend(self._extract_m3u8_formats(
                    format['mediaLocator'], video_id, m3u8_id='hls', fatal=False))

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': video_info['event']['title'],
            'timestamp': unified_timestamp(try_get(video_info, lambda x: x['event']['publishedStartTime'])),
            'thumbnail': video_info.get('thumbnailUrl'),
        }
