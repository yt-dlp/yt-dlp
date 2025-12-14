import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    float_or_none,
    jwt_decode_hs256,
    jwt_encode,
    parse_resolution,
    qualities,
    unified_strdate,
    update_url,
    url_or_none,
    urljoin,
)
from ..utils.traversal import (
    find_element,
    require,
    traverse_obj,
)


class AppleConnectIE(InfoExtractor):
    IE_NAME = 'apple:music:connect'
    IE_DESC = 'Apple Music Connect'

    _BASE_URL = 'https://music.apple.com'
    _QUALITIES = {
        'provisionalUploadVideo': None,
        'sdVideo': 480,
        'sdVideoWithPlusAudio': 480,
        'sd480pVideo': 480,
        '720pHdVideo': 720,
        '1080pHdVideo': 1080,
    }
    _VALID_URL = r'https?://music\.apple\.com/[\w-]+/post/(?P<id>\d+)'
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

    _jwt = None

    @staticmethod
    def _jwt_is_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 120

    def _get_token(self, webpage, video_id):
        if self._jwt and not self._jwt_is_expired(self._jwt):
            return self._jwt

        js_url = traverse_obj(webpage, (
            {find_element(tag='script', attr='crossorigin', value='', html=True)},
            {extract_attributes}, 'src', {urljoin(self._BASE_URL)}, {require('JS URL')}))
        js = self._download_webpage(
            js_url, video_id, 'Downloading token JS', 'Unable to download token JS')

        header = jwt_encode({}, '', headers={'alg': 'ES256', 'kid': 'WebPlayKid'}).split('.')[0]
        self._jwt = self._search_regex(
            fr'(["\'])(?P<jwt>{header}(?:\.[\w-]+){{2}})\1', js, 'JSON Web Token', group='jwt')
        if self._jwt_is_expired(self._jwt):
            raise ExtractorError('The fetched token is already expired')

        return self._jwt

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        videos = self._download_json(
            'https://amp-api.music.apple.com/v1/catalog/us/uploaded-videos',
            video_id, headers={
                'Authorization': f'Bearer {self._get_token(webpage, video_id)}',
                'Origin': self._BASE_URL,
            }, query={'ids': video_id, 'l': 'en-US'})
        attributes = traverse_obj(videos, (
            'data', ..., 'attributes', any, {require('video information')}))

        formats = []
        quality = qualities(list(self._QUALITIES.keys()))
        for format_id, src_url in traverse_obj(attributes, (
            'assetTokens', {dict.items}, lambda _, v: url_or_none(v[1]),
        )):
            formats.append({
                'ext': 'm4v',
                'format_id': format_id,
                'height': self._QUALITIES.get(format_id),
                'quality': quality(format_id),
                'url': src_url,
                **parse_resolution(update_url(src_url, query=None), lenient=True),
            })

        return {
            'id': video_id,
            'formats': formats,
            'thumbnail': self._html_search_meta(
                ['og:image', 'og:image:secure_url', 'twitter:image'], webpage),
            **traverse_obj(attributes, {
                'title': ('name', {str}),
                'duration': ('durationInMilliseconds', {float_or_none(scale=1000)}),
                'upload_date': ('uploadDate', {unified_strdate}),
                'uploader': (('artistName', 'uploadingArtistName'), {str}, any),
                'webpage_url': ('postUrl', {url_or_none}),
            }),
        }
