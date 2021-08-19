# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_parse_qs
from ..utils import (
    xpath_text,
    xpath_element,
    int_or_none,
    parse_iso8601,
    ExtractorError,
)


class RICEIE(InfoExtractor):
    _VALID_URL = r'https?://mediahub\.rice\.edu/app/[Pp]ortal/video\.aspx\?(?P<query>.+)'
    _TEST = {
        'url': 'https://mediahub.rice.edu/app/Portal/video.aspx?PortalID=25ffd62c-3d01-4b29-8c70-7c94270efb3e&DestinationID=66bc9434-03bd-4725-b47e-c659d8d809db&ContentID=YEWIvbhb40aqdjMD1ALSqw',
        'md5': '9b83b4a2eead4912dc3b7fac7c449b6a',
        'info_dict': {
            'id': 'YEWIvbhb40aqdjMD1ALSqw',
            'ext': 'mp4',
            'title': 'Active Learning in Archeology',
            'upload_date': '20140616',
            'timestamp': 1402926346,
        }
    }
    _NS = 'http://schemas.datacontract.org/2004/07/ensembleVideo.Data.Service.Contracts.Models.Player.Config'

    def _real_extract(self, url):
        qs = compat_parse_qs(self._match_valid_url(url).group('query'))
        if not qs.get('PortalID') or not qs.get('DestinationID') or not qs.get('ContentID'):
            raise ExtractorError('Invalid URL', expected=True)

        portal_id = qs['PortalID'][0]
        playlist_id = qs['DestinationID'][0]
        content_id = qs['ContentID'][0]

        content_data = self._download_xml('https://mediahub.rice.edu/api/portal/GetContentTitle', content_id, query={
            'portalId': portal_id,
            'playlistId': playlist_id,
            'contentId': content_id
        })
        metadata = xpath_element(content_data, './/metaData', fatal=True)
        title = xpath_text(metadata, 'primaryTitle', fatal=True)
        encodings = xpath_element(content_data, './/encodings', fatal=True)
        player_data = self._download_xml('https://mediahub.rice.edu/api/player/GetPlayerConfig', content_id, query={
            'temporaryLinkId': xpath_text(encodings, 'temporaryLinkId', fatal=True),
            'contentId': content_id,
        })

        common_fmt = {}
        dimensions = xpath_text(encodings, 'dimensions')
        if dimensions:
            wh = dimensions.split('x')
            if len(wh) == 2:
                common_fmt.update({
                    'width': int_or_none(wh[0]),
                    'height': int_or_none(wh[1]),
                })

        formats = []
        rtsp_path = xpath_text(player_data, self._xpath_ns('RtspPath', self._NS))
        if rtsp_path:
            fmt = {
                'url': rtsp_path,
                'format_id': 'rtsp',
            }
            fmt.update(common_fmt)
            formats.append(fmt)
        for source in player_data.findall(self._xpath_ns('.//Source', self._NS)):
            video_url = xpath_text(source, self._xpath_ns('File', self._NS))
            if not video_url:
                continue
            if '.m3u8' in video_url:
                formats.extend(self._extract_m3u8_formats(video_url, content_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False))
            else:
                fmt = {
                    'url': video_url,
                    'format_id': video_url.split(':')[0],
                }
                fmt.update(common_fmt)
                rtmp = re.search(r'^(?P<url>rtmp://[^/]+/(?P<app>.+))/(?P<playpath>mp4:.+)$', video_url)
                if rtmp:
                    fmt.update({
                        'url': rtmp.group('url'),
                        'play_path': rtmp.group('playpath'),
                        'app': rtmp.group('app'),
                        'ext': 'flv',
                    })
                formats.append(fmt)
        self._sort_formats(formats)

        thumbnails = []
        for content_asset in content_data.findall('.//contentAssets'):
            asset_type = xpath_text(content_asset, 'type')
            if asset_type == 'image':
                image_url = xpath_text(content_asset, 'httpPath')
                if not image_url:
                    continue
                thumbnails.append({
                    'id': xpath_text(content_asset, 'ID'),
                    'url': image_url,
                })

        return {
            'id': content_id,
            'title': title,
            'description': xpath_text(metadata, 'abstract'),
            'duration': int_or_none(xpath_text(metadata, 'duration')),
            'timestamp': parse_iso8601(xpath_text(metadata, 'dateUpdated')),
            'thumbnails': thumbnails,
            'formats': formats,
        }
