import json

from .common import InfoExtractor, float_or_none, parse_iso8601
from ..utils import traverse_obj


class NoveTVBase(InfoExtractor):
    _BASE_DATA = {'deviceInfo':
                  {'adBlocker': False, 'drmSupported': True, 'hdrCapabilities': ['SDR'],
                   'hwDecodingCapabilities': [], 'soundCapabilities': ['STEREO']},
                  'wisteriaProperties': {'platform': 'desktop'}}

    def get_token(self, video_id):
        return traverse_obj(self._download_json('https://public.aurora.enhanced.live/token?realm=it', video_id, 'Downloading token'),
                            ('data', 'attributes', 'token'), expected_type=str)

    def extract_formats(self, playback_info, video_id):
        formats = []

        for fmt in traverse_obj(playback_info, ('data', 'attributes', 'streaming')):
            if fmt.get('type') == 'hls':
                formats.extend(self._extract_m3u8_formats(fmt['url'], video_id))
            elif fmt.get('type') == 'dash':
                formats.extend(self._extract_mpd_formats(fmt['url'], video_id))
        return formats


class NoveTVLiveIE(NoveTVBase):
    _VALID_URL = r'https?://(?:www\.)?nove\.tv/live-streaming-nove'

    _TESTS = [{
        'url': 'https://www.nove.tv/live-streaming-nove',
        'info_dict': {
            'id': 'nove-tv-live',
            'ext': 'mp4',
            'title': r're:Nove TV Live',
            'live_status': 'is_live',
        },
    }]

    def _real_extract(self, url):
        token = self.get_token('nove-tv-live')
        playback_info = self._download_json(
            'https://public.aurora.enhanced.live/playback/v3/channelPlaybackInfo', 'nove-tv-live', 'Downloading playback info',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            data=json.dumps({**self._BASE_DATA, 'channelId': '3'}).encode())

        return {
            'id': 'nove-tv-live',
            'title': 'Nove TV Live',
            'is_live': True,
            'formats': self.extract_formats(playback_info, 'nove-tv-live'),
        }


class NoveTVIE(NoveTVBase):
    _VALID_URL = r'https?://(?:www\.)?nove\.tv/(?!live-streaming-nove)(?P<id>[^/?#]+)'

    _TESTS = [{
        'url': 'https://nove.tv/fratelli-di-crozza-puntata-24-ottobre-2025-video',
        'md5': 'b3627d875a5a3ef1300b704c7a7a7df8',
        'info_dict': {
            'id': '15906',
            'ext': 'mp4',
            'title': 'Fratelli di Crozza | Puntata 24 ottobre 2025',
            'display_id': 'fratelli-di-crozza-puntata-24-ottobre-2025-video',
            'description': 'Sinner, Salvini, De Luca e tanti altri nella nuova puntata di Fratelli di Crozza!\n',
            'duration': 4320.160,
            'thumbnail': 'https://images.aurora.enhanced.live/it/images/video/EHD_612678D/default.jpg',
            'categories': [],
            'series': 'Fratelli di Crozza ',
            'series_id': '571',
            'season': 'Season 9',
            'season_number': 9,
            'episode': 'Puntata 24 ottobre 2025',
            'episode_number': 15,
            'release_timestamp': 1761375600,
            'release_date': '20251025',
        },
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        video_data = self._download_json(f'https://public.aurora.enhanced.live/site/page/{slug}?include=default&filter[environment]=nove',
                                         slug, 'Downloading video data')
        attributes = traverse_obj(video_data, ('included', lambda _, v: v['attributes']['type'] == 'sonicVideoBlock', 'attributes'), get_all=False)
        video_id = attributes['videoId']
        token = self.get_token(video_id)
        playback_info = self._download_json(
            'https://public.aurora.enhanced.live/playback/v3/videoPlaybackInfo', video_id, 'Downloading playback info',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            data=json.dumps({**self._BASE_DATA, 'videoId': video_id}).encode())

        return {
            'id': video_id,
            'title': attributes.get('title'),
            'formats': self.extract_formats(playback_info, video_id),
            'categories': [attributes['category']] if attributes.get('category') else [],
            'display_id': slug,
            **traverse_obj(attributes, ('item', {
                'channel': ('channel'),
                'description': ('description'),
                'duration': ('videoDuration', {float_or_none(scale=1000)}),
                'episode_number': ('episodeNumber'),
                'episode': ('title'),
                'release_timestamp': ('publishStart', {parse_iso8601}),
                'season_number': ('seasonNumber'),
                'series_id': ('show', 'id'),
                'series': ('show', 'title'),
                'thumbnail': ('poster', 'src'),
            })),
        }
