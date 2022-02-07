# coding: utf-8
from .common import InfoExtractor

from ..utils import (
    int_or_none,
    traverse_obj,
)

import json
import re
import uuid


class AmazonStoreIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?amazon\.(?:[a-z]{2,3})(?:\.[a-z]{2})?/(?:[^/]+/)?(?:dp|gp/product)/(?P<id>[^/&#$?]+)'

    _TESTS = [{
        'url': 'https://www.amazon.co.uk/dp/B098XNCHLD/',
        'info_dict': {
            'id': 'B098XNCHLD',
            'title': 'md5:5f3194dbf75a8dcfc83079bd63a2abed',
        },
        'playlist_mincount': 1,
        'playlist': [{
            'info_dict': {
                'id': 'A1F83G8C2ARO7P',
                'ext': 'mp4',
                'title': 'mcdodo usb c cable 100W 5a',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        }]
    }, {
        'url': 'https://www.amazon.in/Sony-WH-1000XM4-Cancelling-Headphones-Bluetooth/dp/B0863TXGM3',
        'info_dict': {
            'id': 'B0863TXGM3',
            'title': 'md5:b0bde4881d3cfd40d63af19f7898b8ff',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'https://www.amazon.com/dp/B0845NXCXF/',
        'info_dict': {
            'id': 'B0845NXCXF',
            'title': 'md5:2145cd4e3c7782f1ee73649a3cff1171',
        },
        'playlist-mincount': 1,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        data_json = self._parse_json(self._html_search_regex(r'var\s?obj\s?=\s?jQuery\.parseJSON\(\'(.*)\'\)', webpage, 'data'), id)
        entries = [{
            'id': video['marketPlaceID'],
            'url': video['url'],
            'title': video.get('title'),
            'thumbnail': video.get('thumbUrl') or video.get('thumb'),
            'duration': video.get('durationSeconds'),
            'height': int_or_none(video.get('videoHeight')),
            'width': int_or_none(video.get('videoWidth')),
        } for video in (data_json.get('videos') or []) if video.get('isVideo') and video.get('url')]
        return self.playlist_result(entries, playlist_id=id, playlist_title=data_json['title'])


class AmazonTrailerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?((amazon\.(?:[a-z]{2,3})(?:\.[a-z]{2})?/gp/video)|(primevideo\.(?:[a-z]{2,3})(?:\.[a-z]{2})?))/detail/(?P<id>[^/&#$?]+)/?.*'

    _TESTS = [{
        'url': 'https://www.amazon.com/gp/video/detail/B07RK3CBNQ/ref=atv_dp_watch_trailer?autoplay=trailer',
        'info_dict': {
            'id': 'B07RK3CBNQ',
            'title': 'Mission: Impossible - Fallout (4K UHD)',
            'ext': 'mp4',
            'duration': 148,
            'description': 'md5:ee89d792fd3fafec8bc71afe94f6a495',
            'display_id': 'amzn1.dv.gti.06b54b63-a783-11c2-6943-2237d7c49aad',
            'manifest_stream_number': 0,
        },
    }, {
        'url': 'https://www.amazon.com/gp/video/detail/B096FT1CFW',
        'info_dict': {
            'id': 'B096FT1CFW',
            'title': 'Demon Slayer -Kimetsu no Yaiba- The Movie: Mugen Train (English Dubbed Version)',
            'ext': 'mp4',
            'display_id': 'amzn1.dv.gti.ab066dd0-d248-4b46-9173-9e7aba38028b',
            'manifest_stream_number': 0,
            'description': 'md5:493293c41bc8bc29fa7ae9f6a82d73d8',
            'duration': 87,
        },
    }, {
        'url': 'https://www.primevideo.com/detail/0FL5RNWP149JC50PVH0Q6PJ2TK/ref=atv_mv_hom_1_c_zbfcqv_brws_2_3',
        'info_dict': {
            'id': '0FL5RNWP149JC50PVH0Q6PJ2TK',
            'title': 'After We Fell',
            'ext': 'mp4',
            'manifest_stream_number': 0,
            'duration': 102,
            'display_id': 'amzn1.dv.gti.074be111-b79a-4288-ae6e-6a7b87d2c608',
            'description': 'md5:3ebd27012d67333ebc3aeb356f847527',
        },
    }, {
        'url': 'https://www.primevideo.com/detail/0SP2T0F2VT868QB7T5OUUV18LG',
        'info_dict': {
            'id': '0SP2T0F2VT868QB7T5OUUV18LG',
            'title': 'Spider-Man: Far From Home',
            'ext': 'mp4',
            'manifest_stream_number': 0,
            'duration': 151,
            'description': 'md5:5cc470d189c0e62d782f700ad46d6015',
            'display_id': 'amzn1.dv.gti.e4b85f95-60b7-b172-232b-3a7f3ffd78c4',
        },
    }]

    def _real_extract(self, url):
        print('WARNING: [AmazonTrailer] Amazon Prime videos use DRM and will not be supported. Downloading the trailer instead')
# self.report_warning('Amazon Prime videos use DRM and will not be supported. Downloading the trailer instead')
# self report warning triggers errors on tests

        video_id = self._match_id(url)

        titleID = None
        title = None
        description = None
        duration = None

        if re.search(r'^https?://(?:www\.)?amazon\.(?:[a-z]{2,3})(?:\.[a-z]{2})?', url) is not None:
            json_url = 'https://atv-ps.amazon.com/cdp/catalog/GetPlaybackResources'
# Download Json with empty data to force POST method, 'deviceTypeID' : 'AOAGZA014O5RE' => WEB
            query = {
                'deviceID': uuid.uuid4(),
                'deviceTypeID': 'AOAGZA014O5RE',
                'firmware': '1',
                'asin': video_id,
                'consumptionType': 'Streaming',
                'desiredResources': 'PlaybackUrls,CuepointPlaylist,CatalogMetadata,SubtitleUrls,ForcedNarratives,TrickplayUrls,TransitionTimecodes,PlaybackSettings,XRayMetadata',
                'resourceUsage': 'CacheResources',
                'videoMaterialType': 'Trailer',
                'deviceProtocolOverride': 'Https',
                'deviceStreamingTechnologyOverride': 'DASH',
                'deviceDrmOverride': 'CENC',
                'deviceBitrateAdaptationsOverride': 'CVBR,CBR',
                'deviceHdrFormatsOverride': 'None',
                'deviceVideoCodecOverride': 'H264',
                'deviceVideoQualityOverride': 'HD',
                'audioTrackId': 'all',
                'languageFeature': 'MLFv2',
                'liveManifestType': 'patternTemplate,accumulating,live',
                'supportedDRMKeyScheme': 'DUAL_KEY',
                'daiLiveManifestType': 'patternTemplate,accumulating,live',
                'titleDecorationScheme': 'primary-content',
                'subtitleFormat': 'TTMLv2',
                'playbackSettingsFormatVersion': '1.0.0',
                'xrayToken': 'XRAY_WEB_2021_V1',
                'xrayPlaybackMode': 'playback',
                'xrayDeviceClass': 'normal',
            }
        else:
            json_url = 'https://atv-ps.primevideo.com/cdp/catalog/GetPlaybackResources'
            webpage = self._download_webpage(url, video_id)
            matches = re.findall(r'<script[^>]*>({.*"titleID":"[^"]*".*})</script>', webpage)
            for match in matches:
                myjson = json.loads(match)
                titleID = titleID or traverse_obj(myjson, ('args', 'titleID'))
                if traverse_obj(myjson, ('props', 'state', 'detail', 'headerDetail', titleID, 'title')) is not None:
                    title = traverse_obj(myjson, ('props', 'state', 'detail', 'headerDetail', titleID, 'title'))
                    description = traverse_obj(myjson, ('props', 'state', 'detail', 'headerDetail', titleID, 'synopsis'))
                    break
            if titleID is None:
                self.report_warning('Can not match in any know JSON structures. Extracting from string to continue.')
                titleID = re.findall(r'"titleID":"([^"]*)"', matches[0])[0]
            query = {
                'deviceID': uuid.uuid4(),
                'deviceTypeID': 'AOAGZA014O5RE',
                'firmware': '1',
                'asin': titleID,
                'consumptionType': 'Streaming',
                'desiredResources': 'PlaybackUrls,CuepointPlaylist',
                'resourceUsage': 'ImmediateConsumption',
                'videoMaterialType': 'Trailer',
                'deviceProtocolOverride': 'Https',
                'deviceStreamingTechnologyOverride': 'DASH',
                'deviceDrmOverride': 'CENC',
                'deviceBitrateAdaptationsOverride': 'CVBR,CBR',
                'deviceHdrFormatsOverride': 'None',
                'deviceVideoCodecOverride': 'H264',
                'deviceVideoQualityOverride': 'HD',
                'audioTrackId': 'all',
                'languageFeature': 'MLFv2',
                'liveManifestType': 'patternTemplate,accumulating,live',
                'supportedDRMKeyScheme': 'DUAL_KEY',
            }

        video = self._download_json(json_url, video_id, 'Downloading JSON for %s' % video_id, fatal=True, data=[], query=query)

        formats = []
        for key, url in video['playbackUrls']['urlSets'].items():
            formats.extend(self._extract_mpd_formats(traverse_obj(url, ('urls', 'manifest', 'url')) + '?amznDtid=AOAGZA014O5RE&encoding=segmentBase',
                           video_id, mpd_id='dash', note='Downloading MPD manifest - %s' % traverse_obj(url, ('urls', 'manifest', 'cdn')), fatal=False))
            duration = duration or int_or_none(traverse_obj(url, ('urls', 'manifest', 'duration')) / 1000)
        self._remove_duplicate_formats(formats)

        return {
            'id': video_id,
            'display_id': titleID or traverse_obj(video, ('catalogMetadata', 'catalog', 'id')),
            'title': title or traverse_obj(video, ('catalogMetadata', 'catalog', 'title')),
            'description': description or traverse_obj(video, ('catalogMetadata', 'catalog', 'synopsis')),
            'duration': duration,
            'formats': formats,
        }
