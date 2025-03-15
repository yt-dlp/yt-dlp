from .common import InfoExtractor
from ..utils import ExtractorError


class MyFreeCamsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:app|share|www)\.myfreecams\.com(?:/room)?/#?(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://app.myfreecams.com/room/stacy_x3',
        'info_dict': {
            'id': 'stacy_x3',
            'title': 're:^stacy_x3 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'ext': 'mp4',
            'live_status': 'is_live',
            'age_limit': 18,
            'thumbnail': 're:https://img.mfcimg.com/photos2/121/12172602/avatar.300x300.jpg\\?nc=\\d+',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Model offline',
    }, {
        'url': 'https://share.myfreecams.com/BUSTY_EMA',
        'info_dict': {
            'id': 'BUSTY_EMA',
            'title': 're:^BUSTY_EMA [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'ext': 'mp4',
            'live_status': 'is_live',
            'age_limit': 18,
            'thumbnail': 're:https://img.mfcimg.com/photos2/295/29538300/avatar.300x300.jpg\\?nc=\\d+',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Model offline',
    }, {
        'url': 'https://www.myfreecams.com/#notbeckyhecky',
        'info_dict': {
            'id': 'notbeckyhecky',
            'title': 're:^notbeckyhecky [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'ext': 'mp4',
            'is_live': True,
            'age_limit': 18,
            'thumbnail': 're:https://img.mfcimg.com/photos2/243/24308977/avatar.300x300.jpg\\?nc=\\d+',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Model offline',
    }]

    def get_required_params(self, webpage):
        sid = self._search_regex(
            [r'data-campreview-sid=["\'](\d+)["\']', r'data-cam-preview-server-id-value=["\'](\d+)["\']'],
            webpage, 'sid',
        )

        mid = self._search_regex(
            [r'data-campreview-mid=["\'](\d+)["\']', r'data-cam-preview-model-id-value=["\'](\d+)["\']'],
            webpage, 'mid',
        )

        webrtc = self._search_regex(
            [r'data-is-webrtc=["\']([^"\']+)["\']', r'data-cam-preview-is-webrtc-value=["\']([^"\']+)["\']'],
            webpage, 'webrtc', default='false',
        )

        snap_url = self._search_regex(
            r'data-cam-preview-snap-url-value=["\']([^"\']+)["\']',
            webpage, 'snap_url',
        )

        webrtc = 'true' if 'mfc_a_' in snap_url else 'false'

        return {
            'sid': sid,
            'mid': str(int(mid) + 100_000_000),
            'a': 'a_' if webrtc == 'true' else '',
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://share.myfreecams.com/' + video_id, video_id)

        if not self._search_regex(r'https://www.myfreecams.com/php/tracking.php\?[^\'"]*model_id=(\d+)[^\'"]*',
                                  webpage, 'model id'):
            raise ExtractorError('Model not found')

        params = self.get_required_params(webpage)
        if not params['sid']:
            raise ExtractorError('Model offline')

        return {
            'id': video_id,
            'title': video_id,
            'is_live': True,
            'formats': self._extract_m3u8_formats(
                'https://edgevideo.myfreecams.com/hls/NxServer/' + params['sid'] + '/ngrp:mfc_' + params['a'] + params['mid'] + '.f4v_mobile/playlist.m3u8',
                video_id, 'mp4', live=True),
            'age_limit': 18,
            'thumbnail': self._search_regex(r'(https?://img\.mfcimg\.com/photos2?/\d+/\d+/avatar\.\d+x\d+.jpg(?:\?nc=\d+)?)', webpage, 'thumbnail', fatal=False),
        }
