from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    parse_resolution,
    qualities,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class AppleConnectIE(InfoExtractor):
    IE_NAME = 'apple:music:connect'
    IE_DESC = 'Apple Music Connect'

    _HEADERS = {
        'Authorization': 'Bearer eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IldlYlBsYXlLaWQifQ.eyJpc3MiOiJBTVBXZWJQbGF5IiwiaWF0IjoxNzQ2NjM3MTY2LCJleHAiOjE3NTM4OTQ3NjYsInJvb3RfaHR0cHNfb3JpZ2luIjpbImFwcGxlLmNvbSJdfQ.ONPUnh6UMOJ1VWujIxxWuTdi2ueBAM01B8xMg4NkNy9mdE_C1Y15-xKGoZ6Qg6mgC-ZMdfFHt5Xf4hL4X4-lMw',
        'Origin': 'https://music.apple.com',
    }
    _QUALITIES = {
        'provisionalUploadVideo': (None, None),
        'sdVideo': (640, 480),
        'sdVideoWithPlusAudio': (640, 480),
        'sd480pVideo': (720, 480),
        '720pHdVideo': (1280, 720),
        '1080pHdVideo': (1440, 1080),
    }
    _VALID_URL = r'https?://music\.apple\.com/\w{0,2}/post/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://music.apple.com/us/post/1018290019',
        'info_dict': {
            'id': '1018290019',
            'ext': 'm4v',
            'title': 'Energy',
            'duration': 177.911,
            'thumbnail': r're:https?://.+\.png',
            'upload_date': '20150710',
            'uploader': 'Drake',
        },
    }, {
        'url': 'https://music.apple.com/us/post/1016746627',
        'info_dict': {
            'id': '1016746627',
            'ext': 'm4v',
            'title': 'Body Shop (Madonna) - Chellous Lima (Acoustic Cover)',
            'duration': 210.278,
            'thumbnail': r're:https?://.+\.png',
            'upload_date': '20150706',
            'uploader': 'Chellous Lima',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if not (videos := traverse_obj(self._download_json(
            'https://amp-api.music.apple.com/v1/catalog/us/uploaded-videos',
            video_id, headers=self._HEADERS, query={'ids': video_id, 'l': 'en-US'},
        ), ('data', ..., 'attributes', any), default={})):
            raise ExtractorError('Failed to fetch video information')

        formats = []
        quality = qualities(list(self._QUALITIES.keys()))
        for format_id, src_url in traverse_obj(videos, (
            'assetTokens', {dict.items}, lambda _, v: url_or_none(v[1]),
        )):
            formats.append({
                'ext': 'm4v',
                'format_id': format_id,
                'quality': quality(format_id),
                'url': src_url,
                **parse_resolution(src_url),
                **traverse_obj(self._QUALITIES, (format_id, {
                    'height': 1,
                    'width': 0,
                })),
            })

        return {
            'id': video_id,
            'formats': formats,
            'thumbnail': self._html_search_meta(
                ('og:image', 'og:image:secure_url', 'twitter:image'), webpage),
            **traverse_obj(videos, {
                'title': ('name', {str}),
                'duration': ('durationInMilliseconds', {float_or_none(scale=1000)}),
                'upload_date': ('uploadDate', {str}, {lambda x: x.replace('-', '')}),
                'uploader': (('artistName', 'uploadingArtistName'), {str}, any),
                'webpage_url': ('postUrl', {url_or_none}),
            }),
        }
