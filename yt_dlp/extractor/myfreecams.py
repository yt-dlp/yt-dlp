import random

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
    traverse_obj,
)


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
            webpage, 'sid', fatal=False,
        )

        mid = self._search_regex(
            [r'data-campreview-mid=["\'](\d+)["\']', r'data-cam-preview-model-id-value=["\'](\d+)["\']'],
            webpage, 'mid', fatal=False,
        )

        webrtc = self._search_regex(
            [r'data-is-webrtc=["\']([^"\']+)["\']', r'data-cam-preview-is-webrtc-value=["\']([^"\']+)["\']'],
            webpage, 'webrtc', default='false',
        )

        snap_url = self._search_regex(
            r'data-cam-preview-snap-url-value=["\']([^"\']+)["\']',
            webpage, 'snap_url', default='',
        )

        webrtc = 'true' if 'mfc_a_' in snap_url else 'false'

        if not sid or not mid:
            return {}

        return {
            'sid': sid,
            'mid': str(int(mid) + 100_000_000),
            'a': 'a_' if webrtc == 'true' else '',
        }

    def webpage_extraction(self, video_id):
        webpage = self._download_webpage('https://share.myfreecams.com/' + video_id, video_id)

        if not self._search_regex(r'https://www.myfreecams.com/php/tracking.php\?[^\'"]*model_id=(\d+)[^\'"]*',
                                  webpage, 'model id'):
            raise ExtractorError('Model not found')

        params = self.get_required_params(webpage)
        if not params.get('sid'):
            raise UserNotLive('Model offline')
        
        formats = self._extract_m3u8_formats(
                'https://edgevideo.myfreecams.com/llhls/NxServer/' + params['sid'] + '/ngrp:mfc_' + params['a'] + params['mid'] + '.f4v_mobile/playlist.m3u8',
                video_id, ext='mp4', m3u8_id='llhls', live=True)
        formats.extend(self._extract_m3u8_formats('https://edgevideo.myfreecams.com/hls/NxServer/' + params['sid'] + '/ngrp:mfc_' + params['a'] + params['mid'] + '.f4v_mobile/playlist.m3u8',
                        video_id, ext='mp4', m3u8_id='hls', live=True))

        return {
            'id': video_id,
            'title': video_id,
            'is_live': True,
            'formats': formats,
            'age_limit': 18,
            'thumbnail': self._search_regex(r'(https?://img\.mfcimg\.com/photos2?/\d+/\d+/avatar\.\d+x\d+.jpg(?:\?nc=\d+)?)', webpage, 'thumbnail', fatal=False),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        user_data = self._download_json(
            'https://api-edge.myfreecams.com/usernameLookup/' + video_id, video_id)

        if not user_data:
            self.report_warning('Unable to get user data from api, falling back to webpage extraction')
            return self.webpage_extraction(video_id)

        user = traverse_obj(user_data, ('result', 'user'))
        if not user:
            raise ExtractorError('Model ' + video_id + ' not found')
        if not user.get('id'):
            raise ExtractorError('Model ' + video_id + ' id not found')
        if user.get('access_level') != 4:
            raise ExtractorError('User ' + video_id + ' is not a model')

        status = user.get('vs')
        if status is None:
            raise UserNotLive('Model ' + video_id + ' offline', expected=True)

        user_sessions = user.get('sessions')
        if not user_sessions or len(user_sessions) < 1:
            self.report_warning('Unable to get user sessions from api, falling back to webpage extraction')
            return self.webpage_extraction(video_id)

        session = next((item for item in user_sessions if item.get('server_name')), None)
        if session is None:
            self.report_warning('Unable to get valid user session from api, falling back to webpage extraction')
            return self.webpage_extraction(video_id)

        vs = session.get('vstate')
        ok_vs = [0, 90]
        if vs not in ok_vs:
            if vs == 127:
                raise UserNotLive('Model ' + video_id + ' is offline', expected=True)
            elif vs == 12:
                raise ExtractorError('Model ' + video_id + ' is in a private show', expected=True)
            elif vs == 13:
                raise ExtractorError('Model ' + video_id + ' is in a group show', expected=True)
            elif vs == 2:
                raise ExtractorError('Model ' + video_id + ' is away', expected=True)
            else:
                raise ExtractorError('Unknown status ' + str(vs) + ' for model ' + video_id)

        server_id = session.get('server_name')[5:]
        phase = session.get('phase')
        mid = int(user.get('id')) + 100_000_000
        rand_val = random.random()

        formats = self._extract_m3u8_formats(
            f'https://edgevideo.myfreecams.com/llhls/NxServer/{server_id}/ngrp:mfc_{phase}{mid}.f4v_cmaf/playlist_sfm4s.m3u8?nc={rand_val}&v=1.97.23',
            video_id, ext='mp4', m3u8_id='llhls', live=True)
        formats.extend(self._extract_m3u8_formats(
            f'https://edgevideo.myfreecams.com/hls/NxServer/{server_id}/ngrp:mfc_{phase}{mid}.f4v_cmaf/playlist_sfm4s.m3u8?nc={rand_val}&v=1.97.23',
            video_id, ext='mp4', m3u8_id='hls', live=True))

        if not formats or len(formats) < 1:
            self.report_warning('Unable to stream urls from api, falling back to webpage extraction')
            return self.webpage_extraction(video_id)

        return {
            'id': video_id,
            'title': video_id,
            'is_live': True,
            'formats': formats,
            'age_limit': 18,
            'thumbnail': user.get('avatar'),
        }
