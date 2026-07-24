from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class TVMonacoIE(InfoExtractor):
    _VALID_URL = r'https?://videos\.tvmonaco\.com/content/(?P<id>[\w-]+)'
    _API_BASE = 'https://videos.tvmonaco.com/api'
    _TESTS = [
        {
            'url': 'https://videos.tvmonaco.com/content/ca-va-lfaire-talk-show-du-28052026-axelle-dekegel-et-alexandre-jelmoni',
            'info_dict': {
                'id': '5e9e01a9-a91b-4054-b046-11e7ce509ba4',
                'ext': 'mp4',
                'title': 'Talk-show du 28/05/2026 - AXELLE DEKEGEL et ALEXANDRE JELMONI',
                'display_id': 'ca-va-lfaire-talk-show-du-28052026-axelle-dekegel-et-alexandre-jelmoni',
                'description': 'Infos, culture, débats, reportage et bonne humeur... Retrouvez ça va l\'faire, votre magazine de société consacré à Monaco et la "French Riviera" du Lundi au Vendredi à 18h',
                'thumbnail': 'https://production.content.okast.tv/2116dc08-1959-465d-857f-3619daefb66b/medias/5e9e01a9-a91b-4054-b046-11e7ce509ba4/cover_picture_16_9_fr_2026.5.27_13.32.48/format=png,quality=80.png',
                'categories': 'Lifestyle',
                'tags': ['riviera', 'matinale', 'lifestyle', 'invité', 'ça va l\'faire'],
                'genres': ['Magazine'],
                'episode': 'Talk-show du 28/05/2026 - AXELLE DEKEGEL et ALEXANDRE JELMONI',
                'timestamp': 1779987191,
                'modified_timestamp': 1779888860,
                'release_date': '20250101',
                'duration': 3129,
                'upload_date': '20260528',
                'modified_date': '20260527',
            },
            'params': {'skip_download': True},  # large videos
        },
    ]

    @staticmethod
    def _clean(dic: dict) -> dict:
        return {k: v for k, v in dic.items() if v not in (None, [], {}, '')}

    def _extract_episode(self, url):
        slug = self._match_id(url)

        # First call: slug -> media metadata. Holds the per-language translations
        # and the media UUID that the playback endpoint needs.
        video_data = self._download_json(
            f'{self._API_BASE}/media/v7/media/{slug}', slug,
            note='Downloading media metadata')

        video_uuid = video_data['uuid']

        # The chosen translation carries the language code, and the playback
        # endpoint expects it -- so it must be resolved BEFORE the playback call
        translation = self._preferred_translation(video_data)

        # Second call: media UUID -> playback source (a single-use, IP-bound,
        # signed HLS master playlist).
        playback = self._download_json(
            f'{self._API_BASE}/offer/v4/media/{video_uuid}/url', video_uuid,
            note='Downloading playback URL',
            query={'language': translation.get('language')})

        # _extract_m3u8_formats fetches the master exactly ONCE, so the single-use
        # token is consumed correctly here
        formats = self._extract_m3u8_formats(
            playback['source'], video_uuid, 'mp4', m3u8_id='hls')

        return {
            'id': video_uuid,
            'display_id': slug,
            'formats': formats,
            **self._extract_metadata(video_data, translation),
        }

    def _preferred_translation(self, video_data):
        default_translation = traverse_obj(
            video_data, ('translations', lambda _, t: t.get('default'), {dict}),
            get_all=False)
        first_translation = traverse_obj(video_data, ('translations', 0, {dict}))
        return default_translation or first_translation or {}

    def _extract_metadata(self, video_data, translation):
        # Season/series info is OPTIONAL -> fatal=False.
        media_uuid = video_data['uuid']
        season_res = self._download_webpage_handle(
            f'{self._API_BASE}/smartlist/v5/serie/{media_uuid}', media_uuid,
            note='Downloading season info', fatal=False, expected_status=404)
        if season_res and season_res[1].status != 404:
            season = self._parse_json(season_res[0], media_uuid, fatal=False) or {}
        else:
            season = {}

        # new_genre carries one genre as per-language translations; take the default
        # title and wrap it, since `genres` is a list field.
        genre = traverse_obj(video_data, (
            'new_genre', 'translations', lambda _, t: t.get('default'), 'title', {str}),
            get_all=False)

        info = {
            'title': translation.get('name'),
            'episode': translation.get('name'),
            'description': translation.get('description'),
            'series': traverse_obj(season, ('serie_translation', 'name', {str})),
            'season': traverse_obj(season, (
                'translations', lambda _, t: t.get('default'), 'name', {str}),
                get_all=False),
            'season_number': int_or_none(season.get('season_rank')),
            'episode_number': int_or_none(season.get('episode_rank')),
            'duration': int_or_none(video_data.get('duration')),
            'timestamp': parse_iso8601(video_data.get('begin_date')),
            'modified_timestamp': parse_iso8601(video_data.get('updated_at')),
            'release_date': unified_strdate(video_data.get('production_date')),
            'tags': traverse_obj(video_data, ('keywords', ..., 'key', {str})),
            'categories': traverse_obj(video_data, (
                'themes', ..., 'translations', lambda _, t: t.get('default'), 'title', {str}),
                get_all=False),
            'genres': [genre] if genre else None,
            # picture is a dict of aspect-ratio variants -> iterate (key, value) pairs
            # and build a thumbnails list, keeping the variant name as the id.
            'thumbnails': traverse_obj(translation, (
                'picture', {dict.items}, lambda _, kv: url_or_none(kv[1].get('url')), {
                    'id': 0,
                    'url': (1, 'url', {url_or_none}),
                    'width': (1, 'width', {int_or_none}),
                    'height': (1, 'height', {int_or_none}),
                })),
        }

        return self._clean(info)

    def _real_extract(self, url):
        return self._extract_episode(url)


class TVMonacoSeasonIE(InfoExtractor):
    _VALID_URL = r'https?://videos\.tvmonaco\.com/season/(?P<id>[\w-]+)'
    _API_BASE = 'https://videos.tvmonaco.com/api'

    _TESTS = [{
        'url': 'https://videos.tvmonaco.com/season/2d34ca3f-94de-41b2-b26d-04f21e6dce41',
        'info_dict': {
            'id': '2d34ca3f-94de-41b2-b26d-04f21e6dce41',
            'title': 'SAISON 03',
        },
        'playlist_mincount': 54,
    }]

    def _real_extract(self, url):
        season_uuid = self._match_id(url)

        smartlist = self._download_json(
            f'{self._API_BASE}/smartlist/v4/smartlist/{season_uuid}', season_uuid,
            note='Downloading season smartlist')

        content_uuids = traverse_obj(smartlist, (
            'smartlist_items', lambda _, i: i.get('content_type') == 'video',
            'content_uuid', {str}))
        entries = [
            self.url_result(f'https://videos.tvmonaco.com/content/{uuid}', TVMonacoIE)
            for uuid in content_uuids
        ]

        title = traverse_obj(
            smartlist, ('translations', lambda _, t: t.get('default'), 'name', {str}),
            get_all=False)

        return self.playlist_result(entries, season_uuid, playlist_title=title)


class TVMonacoSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://videos\.tvmonaco\.com/series/(?P<id>[\w-]+)'
    _API_BASE = 'https://videos.tvmonaco.com/api'

    _TESTS = [{
        'url': 'https://videos.tvmonaco.com/series/c0e9953d-3032-4465-befa-72a6cc953744',
        'info_dict': {
            'id': 'c0e9953d-3032-4465-befa-72a6cc953744',
            'title': "ÇA VA L'FAIRE!",
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        series_id = self._match_id(url)
        smartlist = self._download_json(
            f'{self._API_BASE}/smartlist/v4/smartlist/{series_id}', series_id,
            note='Downloading series smartlist')

        # A series' items are the seasons (content_type "smartlist"); each is handed
        # to the season extractor, so the playlist holds one entry per season.
        season_uuids = traverse_obj(smartlist, (
            'smartlist_items', lambda _, i: i.get('content_type') == 'smartlist',
            'content_uuid', {str}))
        entries = [
            self.url_result(f'https://videos.tvmonaco.com/season/{uuid}', TVMonacoSeasonIE)
            for uuid in season_uuids
        ]

        title = traverse_obj(
            smartlist, ('translations', lambda _, t: t.get('default'), 'name', {str}),
            get_all=False)
        playlist_id = traverse_obj(smartlist, ('uuid', {str})) or series_id
        return self.playlist_result(entries, playlist_id, playlist_title=title)
