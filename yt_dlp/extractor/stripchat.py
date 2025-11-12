from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
    lowercase_escape,
    traverse_obj,
)


class StripchatIE(InfoExtractor):
    _VALID_URL = r'https?://stripchat\.com/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://stripchat.com/Joselin_Flower',
        'info_dict': {
            'id': 'Joselin_Flower',
            'ext': 'mp4',
            'title': 're:^Joselin_Flower [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': str,
            'is_live': True,
            'age_limit': 18,
        },
        'skip': 'Room is offline',
    }, {
        'url': 'https://stripchat.com/Rakhijaan@xh',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, headers=self.geo_verification_headers())
        data = self._search_json(
            r'<script\b[^>]*>\s*window\.__PRELOADED_STATE__\s*=',
            webpage, 'data', video_id, transform_source=lowercase_escape)

        if traverse_obj(data, ('viewCam', 'show', {dict})):
            raise ExtractorError('Model is in a private show', expected=True)
        if not traverse_obj(data, ('viewCam', 'model', 'isLive', {bool})):
            raise UserNotLive(video_id=video_id)

        model_id = data['viewCam']['model']['id']

        formats = []
        # HLS hosts are currently found in .configV3.static.features.hlsFallback.fallbackDomains[]
        # The rest of the path is for backwards compatibility and to guard against A/B testing
        for host in traverse_obj(data, ((('config', 'data'), ('configV3', 'static')), (
                (('features', 'featuresV2'), 'hlsFallback', 'fallbackDomains', ...), 'hlsStreamHost'))):
            formats = self._extract_m3u8_formats(
                f'https://edge-hls.{host}/hls/{model_id}/master/{model_id}_auto.m3u8',
                video_id, ext='mp4', m3u8_id='hls', fatal=False, live=True)
            if formats:
                break
        if not formats:
            self.raise_no_formats('Unable to extract stream host', video_id=video_id)

        return {
            'id': video_id,
            'title': video_id,
            'description': self._og_search_description(webpage),
            'is_live': True,
            'formats': formats,
            # Stripchat declares the RTA meta-tag, but in an non-standard format so _rta_search() can't be used
            'age_limit': 18,
        }
