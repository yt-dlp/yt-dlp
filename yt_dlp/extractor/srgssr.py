# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_urllib_parse_urlparse
from ..utils import (
    ExtractorError,
    parse_iso8601,
    qualities,
)


class SRGSSRIE(InfoExtractor):
    _VALID_URL = r'(?:https?://tp\.srgssr\.ch/p(?:/[^/]+)+\?urn=urn|srgssr):(?P<bu>srf|rts|rsi|rtr|swi):(?:[^:]+:)?(?P<type>video|audio):(?P<id>[0-9a-f\-]{36}|\d+)'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['CH']

    _ERRORS = {
        'AGERATING12': 'To protect children under the age of 12, this video is only available between 8 p.m. and 6 a.m.',
        'AGERATING18': 'To protect children under the age of 18, this video is only available between 11 p.m. and 5 a.m.',
        # 'ENDDATE': 'For legal reasons, this video was only available for a specified period of time.',
        'GEOBLOCK': 'For legal reasons, this video is only available in Switzerland.',
        'LEGAL': 'The video cannot be transmitted for legal reasons.',
        'STARTDATE': 'This video is not yet available. Please try again later.',
    }

    def _get_tokenized_src(self, url, video_id, format_id):
        sp = compat_urllib_parse_urlparse(url).path.split('/')
        token = self._download_json(
            'http://tp.srgssr.ch/akahd/token?acl=/%s/%s/*' % (sp[1], sp[2]),
            video_id, 'Downloading %s token' % format_id, fatal=False) or {}
        auth_params = token.get('token', {}).get('authparams')
        if auth_params:
            url += '?' + auth_params
        return url

    def get_media_data(self, bu, media_type, media_id):
        media_data = self._download_json(
            'http://il.srgssr.ch/integrationlayer/1.0/ue/%s/%s/play/%s.json' % (bu, media_type, media_id),
            media_id)[media_type.capitalize()]

        if media_data.get('block') and media_data['block'] in self._ERRORS:
            message = self._ERRORS[media_data['block']]
            if media_data['block'] == 'GEOBLOCK':
                self.raise_geo_restricted(
                    msg=message, countries=self._GEO_COUNTRIES)
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, message), expected=True)

        return media_data

    def _real_extract(self, url):
        bu, media_type, media_id = re.match(self._VALID_URL, url).groups()

        media_data = self.get_media_data(bu, media_type, media_id)

        metadata = media_data['AssetMetadatas']['AssetMetadata'][0]
        title = metadata['title']
        description = metadata.get('description')
        created_date = media_data.get('createdDate') or metadata.get('createdDate')
        timestamp = parse_iso8601(created_date)

        thumbnails = [{
            'id': image.get('id'),
            'url': image['url'],
        } for image in media_data.get('Image', {}).get('ImageRepresentations', {}).get('ImageRepresentation', [])]

        preference = qualities(['LQ', 'MQ', 'SD', 'HQ', 'HD'])
        formats = []
        for source in media_data.get('Playlists', {}).get('Playlist', []) + media_data.get('Downloads', {}).get('Download', []):
            protocol = source.get('@protocol')
            for asset in source['url']:
                asset_url = asset['text']
                quality = asset['@quality']
                format_id = '%s-%s' % (protocol, quality)
                if protocol.startswith('HTTP-HDS') or protocol.startswith('HTTP-HLS'):
                    asset_url = self._get_tokenized_src(asset_url, media_id, format_id)
                    if protocol.startswith('HTTP-HDS'):
                        formats.extend(self._extract_f4m_formats(
                            asset_url + ('?' if '?' not in asset_url else '&') + 'hdcore=3.4.0',
                            media_id, f4m_id=format_id, fatal=False))
                    elif protocol.startswith('HTTP-HLS'):
                        formats.extend(self._extract_m3u8_formats(
                            asset_url, media_id, 'mp4', 'm3u8_native',
                            m3u8_id=format_id, fatal=False))
                else:
                    formats.append({
                        'format_id': format_id,
                        'url': asset_url,
                        'preference': preference(quality),
                        'ext': 'flv' if protocol == 'RTMP' else None,
                    })
        self._sort_formats(formats)

        return {
            'id': media_id,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'thumbnails': thumbnails,
            'formats': formats,
        }


class SRGSSRPlayIE(InfoExtractor):
    IE_DESC = 'srf.ch, rts.ch, rsi.ch, rtr.ch and swissinfo.ch play sites'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:(?:www|play)\.)?
                        (?P<bu>srf|rts|rsi|rtr|swissinfo)\.ch/play/(?:tv|radio)/
                        (?:
                            [^/]+/(?P<type>video|audio)/[^?]+|
                            popup(?P<type_2>video|audio)player
                        )
                        \?.*?\b(?:id=|urn=urn:[^:]+:video:)(?P<id>[0-9a-f\-]{36}|\d+)
                    '''

    _TESTS = [{
        'url': 'http://www.srf.ch/play/tv/10vor10/video/snowden-beantragt-asyl-in-russland?id=28e1a57d-5b76-4399-8ab3-9097f071e6c5',
        'md5': 'da6b5b3ac9fa4761a942331cef20fcb3',
        'info_dict': {
            'id': '28e1a57d-5b76-4399-8ab3-9097f071e6c5',
            'ext': 'mp4',
            'upload_date': '20130701',
            'title': 'Snowden beantragt Asyl in Russland',
            'timestamp': 1372713995,
        }
    }, {
        # No Speichern (Save) button
        'url': 'http://www.srf.ch/play/tv/top-gear/video/jaguar-xk120-shadow-und-tornado-dampflokomotive?id=677f5829-e473-4823-ac83-a1087fe97faa',
        'md5': '0a274ce38fda48c53c01890651985bc6',
        'info_dict': {
            'id': '677f5829-e473-4823-ac83-a1087fe97faa',
            'ext': 'flv',
            'upload_date': '20130710',
            'title': 'Jaguar XK120, Shadow und Tornado-Dampflokomotive',
            'description': 'md5:88604432b60d5a38787f152dec89cd56',
            'timestamp': 1373493600,
        },
    }, {
        'url': 'http://www.rtr.ch/play/radio/actualitad/audio/saira-tujetsch-tuttina-cuntinuar-cun-sedrun-muster-turissem?id=63cb0778-27f8-49af-9284-8c7a8c6d15fc',
        'info_dict': {
            'id': '63cb0778-27f8-49af-9284-8c7a8c6d15fc',
            'ext': 'mp3',
            'upload_date': '20151013',
            'title': 'Saira: Tujetsch - tuttina cuntinuar cun Sedrun Mustér Turissem',
            'timestamp': 1444750398,
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.rts.ch/play/tv/-/video/le-19h30?id=6348260',
        'md5': '67a2a9ae4e8e62a68d0e9820cc9782df',
        'info_dict': {
            'id': '6348260',
            'display_id': '6348260',
            'ext': 'mp4',
            'duration': 1796,
            'title': 'Le 19h30',
            'description': '',
            'uploader': '19h30',
            'upload_date': '20141201',
            'timestamp': 1417458600,
            'thumbnail': r're:^https?://.*\.image',
            'view_count': int,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }, {
        'url': 'https://www.srf.ch/play/tv/popupvideoplayer?id=c4dba0ca-e75b-43b2-a34f-f708a4932e01',
        'only_matching': True,
    }, {
        'url': 'https://www.srf.ch/play/tv/10vor10/video/snowden-beantragt-asyl-in-russland?urn=urn:srf:video:28e1a57d-5b76-4399-8ab3-9097f071e6c5',
        'only_matching': True,
    }, {
        'url': 'https://www.rts.ch/play/tv/19h30/video/le-19h30?urn=urn:rts:video:6348260',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        bu = mobj.group('bu')
        media_type = mobj.group('type') or mobj.group('type_2')
        media_id = mobj.group('id')
        # other info can be extracted from url + '&layout=json'
        return self.url_result('srgssr:%s:%s:%s' % (bu[:3], media_type, media_id), 'SRGSSR')
