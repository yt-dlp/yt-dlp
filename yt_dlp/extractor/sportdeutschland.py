from .common import InfoExtractor
from ..utils import (
    join_nonempty,
    strip_or_none,
    traverse_obj,
    unified_timestamp,
)


class SportDeutschlandIE(InfoExtractor):
    _VALID_URL = r'https?://sportdeutschland\.tv/(?P<id>(?:[^/]+/)?[^?#/&]+)'
    _TESTS = [{
        'url': 'https://sportdeutschland.tv/blauweissbuchholztanzsport/buchholzer-formationswochenende-2023-samstag-1-bundesliga-landesliga',
        'info_dict': {
            'id': '9839a5c7-0dbb-48a8-ab63-3b408adc7b54',
            'ext': 'mp4',
            'title': 'Buchholzer Formationswochenende 2023 - Samstag - 1. Bundesliga / Landesliga',
            'display_id': 'blauweissbuchholztanzsport/buchholzer-formationswochenende-2023-samstag-1-bundesliga-landesliga',
            'description': 'md5:a288c794a5ee69e200d8f12982f81a87',
            'live_status': 'was_live',
            'channel': 'Blau-Weiss Buchholz Tanzsport',
            'channel_url': 'https://sportdeutschland.tv/blauweissbuchholztanzsport',
            'channel_id': '93ec33c9-48be-43b6-b404-e016b64fdfa3',
            'duration': 32447,
            'upload_date': '20230114',
            'timestamp': 1673733618,
        },
    }, {
        'url': 'https://sportdeutschland.tv/deutscherbadmintonverband/bwf-tour-1-runde-feld-1-yonex-gainward-german-open-2022-0',
        'info_dict': {
            'id': '95c80c52-6b9a-4ae9-9197-984145adfced',
            'ext': 'mp4',
            'title': 'BWF Tour: 1. Runde Feld 1 - YONEX GAINWARD German Open 2022',
            'display_id': 'deutscherbadmintonverband/bwf-tour-1-runde-feld-1-yonex-gainward-german-open-2022-0',
            'description': 'md5:2afb5996ceb9ac0b2ac81f563d3a883e',
            'live_status': 'was_live',
            'channel': 'Deutscher Badminton Verband',
            'channel_url': 'https://sportdeutschland.tv/deutscherbadmintonverband',
            'channel_id': '93ca5866-2551-49fc-8424-6db35af58920',
            'duration': 41097,
            'upload_date': '20220309',
            'timestamp': 1646860727.0,
        },
    }, {
        'url': 'https://sportdeutschland.tv/ggcbremen/formationswochenende-latein-2023',
        'info_dict': {
            'id': '9889785e-55b0-4d97-a72a-ce9a9f157cce',
            'title': 'Formationswochenende Latein 2023 - Samstag',
            'display_id': 'ggcbremen/formationswochenende-latein-2023',
            'description': 'md5:6e4060d40ff6a8f8eeb471b51a8f08b2',
            'live_status': 'was_live',
            'channel': 'Grün-Gold-Club Bremen e.V.',
            'channel_id': '9888f04e-bb46-4c7f-be47-df960a4167bb',
            'channel_url': 'https://sportdeutschland.tv/ggcbremen',
        },
        'playlist_count': 3,
        'playlist': [{
            'info_dict': {
                'id': '988e1fea-9d44-4fab-8c72-3085fb667547',
                'ext': 'mp4',
                'channel_url': 'https://sportdeutschland.tv/ggcbremen',
                'channel_id': '9888f04e-bb46-4c7f-be47-df960a4167bb',
                'channel': 'Grün-Gold-Club Bremen e.V.',
                'duration': 86,
                'title': 'Formationswochenende Latein 2023 - Samstag Part 1',
                'upload_date': '20230225',
                'timestamp': 1677349909,
                'live_status': 'was_live',
            },
        }],
    }, {
        'url': 'https://sportdeutschland.tv/dtb/gymnastik-international-tag-1',
        'info_dict': {
            'id': '95d71b8a-370a-4b87-ad16-94680da18528',
            'ext': 'mp4',
            'title': r're:Gymnastik International - Tag 1 .+',
            'display_id': 'dtb/gymnastik-international-tag-1',
            'channel_id': '936ecef1-2f4a-4e08-be2f-68073cb7ecab',
            'channel': 'Deutscher Turner-Bund',
            'channel_url': 'https://sportdeutschland.tv/dtb',
            'description': 'md5:07a885dde5838a6f0796ee21dc3b0c52',
            'live_status': 'is_live',
        },
        'skip': 'live',
    }]

    def _process_video(self, asset_id, video):
        is_live = video['type'] == 'mux_live'
        token = self._download_json(
            f'https://api.sportdeutschland.tv/api/frontend/asset-token/{asset_id}',
            video['id'], query={'type': video['type'], 'playback_id': video['src']})['token']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://stream.mux.com/{video["src"]}.m3u8?token={token}', video['id'], live=is_live)

        return {
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video, {
                'id': 'id',
                'duration': ('duration', {lambda x: float(x) > 0 and float(x)}),
                'timestamp': ('created_at', {unified_timestamp}),
            }),
        }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        meta = self._download_json(
            f'https://api.sportdeutschland.tv/api/stateless/frontend/assets/{display_id}',
            display_id, query={'access_token': 'true'})

        info = {
            'display_id': display_id,
            **traverse_obj(meta, {
                'id': (('id', 'uuid'), ),
                'title': (('title', 'name'), {strip_or_none}),
                'description': 'description',
                'channel': ('profile', 'name'),
                'channel_id': ('profile', 'id'),
                'is_live': 'currently_live',
                'was_live': 'was_live',
                'channel_url': ('profile', 'slug', {lambda x: f'https://sportdeutschland.tv/{x}'}),
            }, get_all=False),
        }

        parts = traverse_obj(meta, (('livestream', ('videos', ...)), ))
        entries = [{
            'title': join_nonempty(info.get('title'), f'Part {i}', delim=' '),
            **traverse_obj(info, {'channel': 'channel', 'channel_id': 'channel_id',
                                  'channel_url': 'channel_url', 'was_live': 'was_live'}),
            **self._process_video(info['id'], video),
        } for i, video in enumerate(parts, 1)]

        return {
            '_type': 'multi_video',
            **info,
            'entries': entries,
        } if len(entries) > 1 else {
            **info,
            **entries[0],
            'title': info.get('title'),
        }
