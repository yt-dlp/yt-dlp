from .common import InfoExtractor
from ..utils import (
    join_nonempty,
    strip_or_none,
    traverse_obj,
    unified_timestamp,
)


class SportDeutschlandIE(InfoExtractor):
    _VALID_URL = r'https?://(?:player\.)?sportdeutschland\.tv/(?P<id>(?:[^/?#]+/)?[^?#/&]+)'
    _TESTS = [{
        # Single-part video, direct link
        'url': 'https://sportdeutschland.tv/rostock-griffins/gfl2-rostock-griffins-vs-elmshorn-fighting-pirates',
        'md5': '35c11a19395c938cdd076b93bda54cde',
        'info_dict': {
            'id': '9f27a97d-1544-4d0b-aa03-48d92d17a03a',
            'ext': 'mp4',
            'title': 'GFL2: Rostock Griffins vs. Elmshorn Fighting Pirates',
            'display_id': 'rostock-griffins/gfl2-rostock-griffins-vs-elmshorn-fighting-pirates',
            'channel': 'Rostock Griffins',
            'channel_url': 'https://sportdeutschland.tv/rostock-griffins',
            'live_status': 'was_live',
            'description': 'md5:60cb00067e55dafa27b0933a43d72862',
            'channel_id': '9635f21c-3f67-4584-9ce4-796e9a47276b',
            'timestamp': 1749913117,
            'upload_date': '20250614',
            'duration': 12287.0,
        },
    }, {
        # Single-part video, embedded player link
        'url': 'https://player.sportdeutschland.tv/9e9619c4-7d77-43c4-926d-49fb57dc06dc',
        'info_dict': {
            'id': '9f27a97d-1544-4d0b-aa03-48d92d17a03a',
            'ext': 'mp4',
            'title': 'GFL2: Rostock Griffins vs. Elmshorn Fighting Pirates',
            'display_id': '9e9619c4-7d77-43c4-926d-49fb57dc06dc',
            'channel': 'Rostock Griffins',
            'channel_url': 'https://sportdeutschland.tv/rostock-griffins',
            'live_status': 'was_live',
            'description': 'md5:60cb00067e55dafa27b0933a43d72862',
            'channel_id': '9635f21c-3f67-4584-9ce4-796e9a47276b',
            'timestamp': 1749913117,
            'upload_date': '20250614',
            'duration': 12287.0,
        },
        'params': {'skip_download': True},
    }, {
        # Multi-part video
        'url': 'https://sportdeutschland.tv/rhine-ruhr-2025-fisu-world-university-games/volleyball-w-japan-vs-brasilien-halbfinale-2',
        'info_dict': {
            'id': '9f63d737-2444-4e3a-a1ea-840df73fd481',
            'display_id': 'rhine-ruhr-2025-fisu-world-university-games/volleyball-w-japan-vs-brasilien-halbfinale-2',
            'title': 'Volleyball w: Japan vs. Braslien - Halbfinale 2',
            'description': 'md5:0a17da15e48a687e6019639c3452572b',
            'channel': 'Rhine-Ruhr 2025 FISU World University Games',
            'channel_id': '9f5216be-a49d-470b-9a30-4fe9df993334',
            'channel_url': 'https://sportdeutschland.tv/rhine-ruhr-2025-fisu-world-university-games',
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
                'channel_url': 'https://sportdeutschland.tv/rhine-ruhr-2025-fisu-world-university-games',
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
                'channel_url': 'https://sportdeutschland.tv/rhine-ruhr-2025-fisu-world-university-games',
                'duration': 14773.0,
                'timestamp': 1753128421,
                'upload_date': '20250721',
                'live_status': 'was_live',
            },
        }],
    }, {
        # Livestream
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
            f'https://api.sportdeutschland.tv/api/web/personal/asset-token/{asset_id}',
            video['id'], query={'type': video['type'], 'playback_id': video['src']},
            headers={'Referer': 'https://sportdeutschland.tv/'})['token']
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
