from .common import InfoExtractor

from ..utils import (
    format_field,
    traverse_obj,
    unified_timestamp,
    strip_or_none
)


class SportDeutschlandIE(InfoExtractor):
    _VALID_URL = r'https?://sportdeutschland\.tv/(?P<id>(?:[^/]+/)?[^?#/&]+)'
    _TESTS = [{
        'url': 'https://sportdeutschland.tv/blauweissbuchholztanzsport/buchholzer-formationswochenende-2023-samstag-1-bundesliga-landesliga',
        'info_dict': {
            'id': '983758e9-5829-454d-a3cf-eb27bccc3c94',
            'ext': 'mp4',
            'title': 'Buchholzer Formationswochenende 2023 - Samstag - 1. Bundesliga / Landesliga',
            'description': 'md5:a288c794a5ee69e200d8f12982f81a87',
            'live_status': 'was_live',
            'channel': 'Blau-Weiss Buchholz Tanzsport',
            'channel_url': 'https://sportdeutschland.tv/blauweissbuchholztanzsport',
            'channel_id': '93ec33c9-48be-43b6-b404-e016b64fdfa3',
            'display_id': '9839a5c7-0dbb-48a8-ab63-3b408adc7b54',
            'duration': 32447,
            'upload_date': '20230114',
            'timestamp': 1673730018.0,
        }
    }, {
        'url': 'https://sportdeutschland.tv/deutscherbadmintonverband/bwf-tour-1-runde-feld-1-yonex-gainward-german-open-2022-0',
        'info_dict': {
            'id': '95b97d9a-04f6-4880-9039-182985c33943',
            'ext': 'mp4',
            'title': 'BWF Tour: 1. Runde Feld 1 - YONEX GAINWARD German Open 2022',
            'description': 'md5:2afb5996ceb9ac0b2ac81f563d3a883e',
            'live_status': 'was_live',
            'channel': 'Deutscher Badminton Verband',
            'channel_url': 'https://sportdeutschland.tv/deutscherbadmintonverband',
            'channel_id': '93ca5866-2551-49fc-8424-6db35af58920',
            'display_id': '95c80c52-6b9a-4ae9-9197-984145adfced',
            'duration': 41097,
            'upload_date': '20220309',
            'timestamp': 1646860727.0,
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        meta = self._download_json(
            'https://api.sportdeutschland.tv/api/stateless/frontend/assets/' + display_id,
            display_id, query={'access_token': 'true'})

        asset_id = traverse_obj(meta, 'id', 'uuid')

        info = {
            'id': asset_id,
            'channel_url': format_field(meta, ('profile', 'slug'), 'https://sportdeutschland.tv/%s'),
            **traverse_obj(meta, {
                'title': (('title', 'name'), {strip_or_none}),
                'description': 'description',
                'channel': ('profile', 'name'),
                'channel_id': ('profile', 'id'),
                'is_live': 'currently_live',
                'was_live': 'was_live'
            }, get_all=False)
        }

        videos = meta.get('videos') or []

        if len(videos) > 1:
            info.update({
                '_type': 'multi_video',
                'entries': self.processVideoOrStream(asset_id, video)
            } for video in enumerate(videos) if video.get('formats'))

        elif len(videos) == 1:
            info.update(
                self.processVideoOrStream(asset_id, videos[0])
            )

        livestream = meta.get('livestream')

        if livestream is not None:
            info.update(
                self.processVideoOrStream(asset_id, livestream)
            )

        return info

    def process_video_or_stream(self, asset_id, video):
        video_id = video['id']
        video_src = video['src']
        video_type = video['type']

        token = self._download_json(
            f'https://api.sportdeutschland.tv/api/frontend/asset-token/{asset_id}',
            video_id, query={'type': video_type, 'playback_id': video_src})['token']
        formats = self._extract_m3u8_formats(f'https://stream.mux.com/{video_src}.m3u8?token={token}', video_id)

        video_data = {
            'display_id': video_id,
            'formats': formats,
        }
        if video_type == 'mux_vod':
            video_data.update({
                'duration': video.get('duration'),
                'timestamp': unified_timestamp(video.get('created_at'))
            })

        return video_data
