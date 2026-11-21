from .common import InfoExtractor
from ..utils import (
    strip_or_none,
    traverse_obj,
    unified_timestamp,
)


class SportDeutschlandIE(InfoExtractor):
    IE_NAME = 'sporteurope'
    _VALID_URL = r'https?://(?:player\.)?sporteurope\.tv/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?P<id>[^?#]+)'
    _TESTS = [{
        # Single-part video, direct link
        'url': 'https://sporteurope.tv/rostock-griffins/gfl2-rostock-griffins-vs-elmshorn-fighting-pirates',
        'md5': '35c11a19395c938cdd076b93bda54cde',
        'info_dict': {
            'id': '9e9619c4-7d77-43c4-926d-49fb57dc06dc',
            'ext': 'mp4',
            'title': 'GFL2: Rostock Griffins vs. Elmshorn Fighting Pirates',
            'display_id': 'rostock-griffins/gfl2-rostock-griffins-vs-elmshorn-fighting-pirates',
            'channel': 'Rostock Griffins',
            'channel_url': 'https://sporteurope.tv/rostock-griffins',
            'live_status': 'was_live',
            'description': r're:Video-Livestream des Spiels Rostock Griffins vs\. Elmshorn Fighting Pirates.+',
            'channel_id': '9635f21c-3f67-4584-9ce4-796e9a47276b',
            'duration': 12287.0,
        },
    }, {
        # Single-part video, embedded player link
        'url': 'https://player.sporteurope.tv/9e9619c4-7d77-43c4-926d-49fb57dc06dc',
        'info_dict': {
            'id': '9e9619c4-7d77-43c4-926d-49fb57dc06dc',
            'ext': 'mp4',
            'title': 'GFL2: Rostock Griffins vs. Elmshorn Fighting Pirates',
            'display_id': '9e9619c4-7d77-43c4-926d-49fb57dc06dc',
            'channel': 'Rostock Griffins',
            'channel_url': 'https://sporteurope.tv/rostock-griffins',
            'live_status': 'was_live',
            'description': r're:Video-Livestream des Spiels Rostock Griffins vs\. Elmshorn Fighting Pirates.+',
            'channel_id': '9635f21c-3f67-4584-9ce4-796e9a47276b',
            'duration': 12287.0,
        },
        'params': {'skip_download': True},
    }, {
        # Single-part video, match locale prefixed URL
        'url': 'https://sporteurope.tv/en/deutsche-turnliga/2025-iwa-nachwuchsbundesliga-dtl-finale-turnen-heidelberg',
        'info_dict': {
            'id': 'a0731851-5ac2-4024-a20f-20c5fc1655de',
            'title': '2025 | IWA-Nachwuchsbundesliga | DTL-Finale Turnen | Heidelberg',
            'ext': 'mp4',
            'display_id': 'deutsche-turnliga/2025-iwa-nachwuchsbundesliga-dtl-finale-turnen-heidelberg',
            'channel': 'Deutsche Turnligaaaa',
            'channel_id': '936ed054-572c-48a6-8132-4a20ea81bbca',
            'channel_url': 'https://sporteurope.tv/deutsche-turnliga',
            'live_status': 'was_live',
        },
        'params': {'skip_download': True},
    }, {
        # Multi-part video
        'url': 'https://sporteurope.tv/rhine-ruhr-2025-fisu-world-university-games/volleyball-w-japan-vs-brasilien-halbfinale-2',
        'info_dict': {
            'id': '9f63d737-2444-4e3a-a1ea-840df73fd481',
            'display_id': 'rhine-ruhr-2025-fisu-world-university-games/volleyball-w-japan-vs-brasilien-halbfinale-2',
            'title': 'Volleyball w: Japan vs. Braslien - Halbfinale 2',
            'description': 'md5:0a17da15e48a687e6019639c3452572b',
            'channel': 'Rhine-Ruhr 2025 FISU World University Games',
            'channel_id': '9f5216be-a49d-470b-9a30-4fe9df993334',
            'channel_url': 'https://sporteurope.tv/rhine-ruhr-2025-fisu-world-university-games',
            'live_status': 'was_live',
        },
        'playlist_count': 2,
        'playlist': [{
            'info_dict': {
                'id': '9f725a94-d43e-40ff-859d-13da3081bb04',
                'ext': 'mp4',
                'title': 'Volleyball w: Japan vs. Braslien - Halbfinale 2 Part 1',
                'channel': 'Rhine-Ruhr 2025 FISU World University Games',
                'channel_id': '9f5216be-a49d-470b-9a30-4fe9df993334',
                'channel_url': 'https://sporteurope.tv/rhine-ruhr-2025-fisu-world-university-games',
                'duration': 14773.0,
                'timestamp': 1753085197,
                'upload_date': '20250721',
                'live_status': 'was_live',
            },
        }, {
            'info_dict': {
                'id': '9f725a94-370e-4477-89ac-1751098e3217',
                'ext': 'mp4',
                'title': 'Volleyball w: Japan vs. Braslien - Halbfinale 2 Part 2',
                'channel': 'Rhine-Ruhr 2025 FISU World University Games',
                'channel_id': '9f5216be-a49d-470b-9a30-4fe9df993334',
                'channel_url': 'https://sporteurope.tv/rhine-ruhr-2025-fisu-world-university-games',
                'duration': 14773.0,
                'timestamp': 1753128421,
                'upload_date': '20250721',
                'live_status': 'was_live',
            },
        }],
        'skip': '404 Not Found',
    }, {
        # Livestream
        'url': 'https://sporteurope.tv/dtb/gymnastik-international-tag-1',
        'info_dict': {
            'id': '95d71b8a-370a-4b87-ad16-94680da18528',
            'ext': 'mp4',
            'title': r're:Gymnastik International - Tag 1 .+',
            'display_id': 'dtb/gymnastik-international-tag-1',
            'channel_id': '936ecef1-2f4a-4e08-be2f-68073cb7ecab',
            'channel': 'Deutscher Turner-Bund',
            'channel_url': 'https://sporteurope.tv/dtb',
            'description': 'md5:07a885dde5838a6f0796ee21dc3b0c52',
            'live_status': 'is_live',
        },
        'skip': 'live',
    }]

    def _process_video(self, asset_id, video):
        is_live = video['type'] == 'mux_live'
        token = self._download_json(
            f'https://api.sporteurope.tv/api/web/personal/asset-token/{asset_id}',
            video['id'], query={'type': video['type'], 'playback_id': video['src']},
            headers={'Referer': 'https://sporteurope.tv/'})['token']
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
        display_id = self._match_id(url).rstrip('/')
        meta = self._download_json(
            f'https://api.sporteurope.tv/api/web/public/assets/{display_id}',
            display_id, note='Downloading asset metadata')

        asset_id = traverse_obj(meta, (('id', 'uuid'), ), get_all=False)

        info = {
            'id': asset_id,
            'display_id': display_id,
            **traverse_obj(meta, {
                'title': (('title', 'name'), {strip_or_none}),
                'description': 'description',
                'channel': ('profile', 'name'),
                'channel_id': ('profile', 'id'),
                'is_live': 'currently_live',
                'was_live': 'was_live',
                'channel_url': ('profile', 'slug', {lambda x: f'https://sporteurope.tv/{x}'}),
                'duration': ('duration_in_seconds', {lambda x: float(x) > 0 and float(x)}),
            }, get_all=False),
        }

        player_meta = self._download_json(
            f'https://api.sporteurope.tv/api/web-player/personal/assets/{asset_id}',
            display_id, note='Downloading player metadata',
            headers={
                'Origin': 'https://sporteurope.tv',
                'Referer': 'https://sporteurope.tv/',
                'x-version': '2',
            })

        formats, subtitles = [], {}
        for track in traverse_obj(player_meta, ('tracks', ...)):
            language = traverse_obj(track, 'audio_language')
            for source in traverse_obj(track, ('sources', ...)):
                hls_url = traverse_obj(source, 'hls')
                if not hls_url:
                    continue
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    hls_url, display_id, 'mp4',
                    live=info.get('is_live'), fatal=False)
                for f in fmts:
                    if language:
                        f['language'] = language
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

        info['formats'] = formats
        info['subtitles'] = subtitles
        return info
