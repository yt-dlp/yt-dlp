# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import int_or_none


class PerformGroupIE(InfoExtractor):
    _VALID_URL = r'https?://player\.performgroup\.com/eplayer(?:/eplayer\.html|\.js)#/?(?P<id>[0-9a-f]{26})\.(?P<auth_token>[0-9a-z]{26})'
    _TESTS = [{
        # http://www.faz.net/aktuell/sport/fussball/wm-2018-playoffs-schweiz-besiegt-nordirland-1-0-15286104.html
        'url': 'http://player.performgroup.com/eplayer/eplayer.html#d478c41c5d192f56b9aa859de8.1w4crrej5w14e1ed4s1ce4ykab',
        'md5': '259cb03d142e2e52471e8837ecacb29f',
        'info_dict': {
            'id': 'xgrwobuzumes1lwjxtcdpwgxd',
            'ext': 'mp4',
            'title': 'Liga MX: Keine Einsicht nach Horrorfoul',
            'description': 'md5:7cd3b459c82725b021e046ab10bf1c5b',
            'timestamp': 1511533477,
            'upload_date': '20171124',
        }
    }]

    def _call_api(self, service, auth_token, content_id, referer_url):
        return self._download_json(
            'http://ep3.performfeeds.com/ep%s/%s/%s/' % (service, auth_token, content_id),
            content_id, headers={
                'Referer': referer_url,
                'Origin': 'http://player.performgroup.com',
            }, query={
                '_fmt': 'json',
            })

    def _real_extract(self, url):
        player_id, auth_token = re.search(self._VALID_URL, url).groups()
        bootstrap = self._call_api('bootstrap', auth_token, player_id, url)
        video = bootstrap['config']['dataSource']['sourceItems'][0]['videos'][0]
        video_id = video['uuid']
        vod = self._call_api('vod', auth_token, video_id, url)
        media = vod['videos']['video'][0]['media']

        formats = []
        hls_url = media.get('hls', {}).get('url')
        if hls_url:
            formats.extend(self._extract_m3u8_formats(hls_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False))

        hds_url = media.get('hds', {}).get('url')
        if hds_url:
            formats.extend(self._extract_f4m_formats(hds_url + '?hdcore', video_id, f4m_id='hds', fatal=False))

        for c in media.get('content', []):
            c_url = c.get('url')
            if not c_url:
                continue
            tbr = int_or_none(c.get('bitrate'), 1000)
            format_id = 'http'
            if tbr:
                format_id += '-%d' % tbr
            formats.append({
                'format_id': format_id,
                'url': c_url,
                'tbr': tbr,
                'width': int_or_none(c.get('width')),
                'height': int_or_none(c.get('height')),
                'filesize': int_or_none(c.get('fileSize')),
                'vcodec': c.get('type'),
                'fps': int_or_none(c.get('videoFrameRate')),
                'vbr': int_or_none(c.get('videoRate'), 1000),
                'abr': int_or_none(c.get('audioRate'), 1000),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video['title'],
            'description': video.get('description'),
            'thumbnail': video.get('poster'),
            'duration': int_or_none(video.get('duration')),
            'timestamp': int_or_none(video.get('publishedTime'), 1000),
            'formats': formats,
        }
