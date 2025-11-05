import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
    urljoin,
)
from ..utils.traversal import require, traverse_obj


class MaveIE(InfoExtractor):
    IE_NAME = 'mave'
    _VALID_URL = r'https?://(?P<channel>[\w-]+)\.mave\.digital/(?P<id>ep-\d+)'
    _TESTS = [{
        'url': 'https://ochenlichnoe.mave.digital/ep-25',
        'md5': 'aa3e513ef588b4366df1520657cbc10c',
        'info_dict': {
            'id': '4035f587-914b-44b6-aa5a-d76685ad9bc2',
            'ext': 'mp3',
            'display_id': 'ochenlichnoe-ep-25',
            'title': 'Между мной и миром: психология самооценки',
            'description': 'md5:4b7463baaccb6982f326bce5c700382a',
            'uploader': 'Самарский университет',
            'channel': 'Очень личное',
            'channel_id': 'ochenlichnoe',
            'channel_url': 'https://ochenlichnoe.mave.digital/',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'duration': 3744,
            'thumbnail': r're:https://.+/storage/podcasts/.+\.jpg',
            'series': 'Очень личное',
            'series_id': '2e0c3749-6df2-4946-82f4-50691419c065',
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 3',
            'episode_number': 3,
            'timestamp': 1747817300,
            'upload_date': '20250521',
        },
    }, {
        'url': 'https://budem.mave.digital/ep-12',
        'md5': 'e1ce2780fcdb6f17821aa3ca3e8c919f',
        'info_dict': {
            'id': '41898bb5-ff57-4797-9236-37a8e537aa21',
            'ext': 'mp3',
            'display_id': 'budem-ep-12',
            'title': 'Екатерина Михайлова: "Горе от ума" не про женщин написана',
            'description': 'md5:fa3bdd59ee829dfaf16e3efcb13f1d19',
            'uploader': 'Полина Цветкова+Евгения Акопова',
            'channel': 'Все там будем',
            'channel_id': 'budem',
            'channel_url': 'https://budem.mave.digital/',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
            'duration': 3664,
            'thumbnail': r're:https://.+/storage/podcasts/.+\.jpg',
            'series': 'Все там будем',
            'series_id': 'fe9347bf-c009-4ebd-87e8-b06f2f324746',
            'season': 'Season 2',
            'season_number': 2,
            'episode': 'Episode 5',
            'episode_number': 5,
            'timestamp': 1735538400,
            'upload_date': '20241230',
        },
    }]
    _API_BASE_URL = 'https://api.mave.digital/'

    def _real_extract(self, url):
        channel_id, slug = self._match_valid_url(url).group('channel', 'id')
        display_id = f'{channel_id}-{slug}'
        webpage = self._download_webpage(url, display_id)
        data = traverse_obj(
            self._search_nuxt_json(webpage, display_id),
            ('data', lambda _, v: v['activeEpisodeData'], any, {require('podcast data')}))

        return {
            'display_id': display_id,
            'channel_id': channel_id,
            'channel_url': f'https://{channel_id}.mave.digital/',
            'vcodec': 'none',
            'thumbnail': re.sub(r'_\d+(?=\.(?:jpg|png))', '', self._og_search_thumbnail(webpage, default='')) or None,
            **traverse_obj(data, ('activeEpisodeData', {
                'url': ('audio', {urljoin(self._API_BASE_URL)}),
                'id': ('id', {str}),
                'title': ('title', {str}),
                'description': ('description', {clean_html}),
                'duration': ('duration', {int_or_none}),
                'season_number': ('season', {int_or_none}),
                'episode_number': ('number', {int_or_none}),
                'view_count': ('listenings', {int_or_none}),
                'like_count': ('reactions', lambda _, v: v['type'] == 'like', 'count', {int_or_none}, any),
                'dislike_count': ('reactions', lambda _, v: v['type'] == 'dislike', 'count', {int_or_none}, any),
                'age_limit': ('is_explicit', {bool}, {lambda x: 18 if x else None}),
                'timestamp': ('publish_date', {parse_iso8601}),
            })),
            **traverse_obj(data, ('podcast', 'podcast', {
                'series_id': ('id', {str}),
                'series': ('title', {str}),
                'channel': ('title', {str}),
                'uploader': ('author', {str}),
            })),
        }


class MaveChannelIE(InfoExtractor):
    IE_NAME = 'mave:channel'
    _VALID_URL = r'https?://(?P<id>[\w-]+)\.mave\.digital/?$'
    _TESTS = [{
        'url': 'https://budem.mave.digital/',
        'info_dict': {
            'id': 'budem',
            'title': 'Все там будем',
            'description': 'md5:f04ae12a42be0f1d765c5e326b41987a',
        },
        'playlist_mincount': 15,
    }, {
        'url': 'https://ochenlichnoe.mave.digital/',
        'info_dict': {
            'id': 'ochenlichnoe',
            'title': 'Очень личное',
            'description': 'md5:ee36a6a52546b91b487fe08c552fdbb2',
        },
        'playlist_mincount': 20,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        webpage = self._download_webpage(url, channel_id)

        nuxt_data = self._search_nuxt_json(webpage, channel_id)

        channel_title = traverse_obj(nuxt_data, (
            'pinia', 'common', 'podcast', 'podcast', 'title'))
        channel_description = traverse_obj(nuxt_data, (
            'pinia', 'common', 'podcast', 'podcast', 'description'))

        episodes_data = traverse_obj(nuxt_data, ('pinia', 'common', 'episodes'))

        entries = []
        for episode in episodes_data[::-1]:
            episode_id = traverse_obj(episode, 'id')
            episode_code = 'ep-' + str(traverse_obj(episode, 'code'))
            if episode_code:
                entries.append(self.url_result(
                    f'https://{channel_id}.mave.digital/{episode_code}',
                    ie=MaveIE.ie_key(),
                    video_id=episode_id,
                ))

        return self.playlist_result(
            entries, channel_id, channel_title, channel_description)
