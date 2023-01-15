import time
import datetime

from .common import InfoExtractor


class SportDeutschlandIE(InfoExtractor):
    _VALID_URL = r'https?://sportdeutschland\.tv/(?P<id>(?:[^/]+/)?[^?#/&]+)'
    _TESTS = [{
        'url': 'https://sportdeutschland.tv/blauweissbuchholztanzsport/buchholzer-formationswochenende-2023-samstag-1-bundesliga-landesliga',
        'info_dict': {
            'id': '983758e9-5829-454d-a3cf-eb27bccc3c94',
            'ext': 'mp4',
            'title': 'Buchholzer Formationswochenende 2023 - Samstag - 1. Bundesliga / Landesliga',
            'description': '14:30 Uhr Turnierbeginn Landesliga Nord Gruppe A - 16:10 Uhr Finalrunde Landesliga Nord Gruppe A - 17:15 Uhr Siegerehrung Landesliga Nord Gruppe A - 19:00 Uhr Turnierbeginn 1. Bundesliga - 21:20 Uhr Finalrunde 1. Bundesliga - 22:30 Uhr Siegerehrung 1. Bundesliga',
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

        asset_id = meta.get('id') or meta.get('uuid')
        profile = meta.get('profile')

        info = {
            'id': asset_id,
            'title': (meta.get('title') or meta.get('name')).strip(),
            'description': meta.get('description'),
            'channel': profile.get('name'),
            'channel_id': profile.get('id'),
            'channel_url': 'https://sportdeutschland.tv/' + profile.get('slug'),
            'is_live': meta.get('currently_live'),
            'was_live': meta.get('was_live')
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

    def processVideoOrStream(self, asset_id, video):
        video_id = video.get('id')
        video_src = video.get('src')
        video_type = video.get('type')

        token_data = self._download_json(
            'https://api.sportdeutschland.tv/api/frontend/asset-token/' + asset_id
            + '?type=' + video_type
            + '&playback_id=' + video_src,
            video_id
        )

        m3u8_url = "https://stream.mux.com/" + video_src + '.m3u8?token=' + token_data.get('token')
        formats = self._extract_m3u8_formats(m3u8_url, video_id)

        videoData = {
            'display_id': video_id,
            'formats': formats,
        }
        if video_type == 'mux_vod':
            videoData.update({
                'duration': video.get('duration'),
                'timestamp': time.mktime(datetime.datetime.fromisoformat(video.get('created_at')).timetuple())
            })

        return videoData
