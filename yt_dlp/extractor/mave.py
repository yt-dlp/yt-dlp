import functools
import math

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    clean_html,
    int_or_none,
    parse_iso8601,
    urljoin,
)
from ..utils.traversal import require, traverse_obj


class MaveBaseIE(InfoExtractor):
    _API_BASE_URL = 'https://api.mave.digital/v1/website'
    _API_BASE_STORAGE_URL = 'https://store.cloud.mts.ru/mave/'

    def _load_channel_meta(self, channel_id, display_id):
        return traverse_obj(self._download_json(
            f'{self._API_BASE_URL}/{channel_id}/', display_id,
            note='Downloading channel metadata'), 'podcast')

    def _load_episode_meta(self, channel_id, episode_code, display_id):
        return self._download_json(
            f'{self._API_BASE_URL}/{channel_id}/episodes/{episode_code}',
            display_id, note='Downloading episode metadata')

    def _create_entry(self, channel_id, channel_meta, episode_meta):
        episode_code = traverse_obj(episode_meta, ('code', {int}, {require('episode code')}))
        return {
            'display_id': f'{channel_id}-{episode_code}',
            'extractor_key': MaveIE.ie_key(),
            'extractor': MaveIE.IE_NAME,
            'webpage_url': f'https://{channel_id}.mave.digital/ep-{episode_code}',
            'channel_id': channel_id,
            'channel_url': f'https://{channel_id}.mave.digital/',
            'vcodec': 'none',
            **traverse_obj(episode_meta, {
                'id': ('id', {str}),
                'url': ('audio', {urljoin(self._API_BASE_STORAGE_URL)}),
                'title': ('title', {str}),
                'description': ('description', {clean_html}),
                'thumbnail': ('image', {urljoin(self._API_BASE_STORAGE_URL)}),
                'duration': ('duration', {int_or_none}),
                'season_number': ('season', {int_or_none}),
                'episode_number': ('number', {int_or_none}),
                'view_count': ('listenings', {int_or_none}),
                'like_count': ('reactions', lambda _, v: v['type'] == 'like', 'count', {int_or_none}, any),
                'dislike_count': ('reactions', lambda _, v: v['type'] == 'dislike', 'count', {int_or_none}, any),
                'age_limit': ('is_explicit', {bool}, {lambda x: 18 if x else None}),
                'timestamp': ('publish_date', {parse_iso8601}),
            }),
            **traverse_obj(channel_meta, {
                'series_id': ('id', {str}),
                'series': ('title', {str}),
                'channel': ('title', {str}),
                'uploader': ('author', {str}),
            }),
        }


class MaveIE(MaveBaseIE):
    IE_NAME = 'mave'
    _VALID_URL = r'https?://(?P<channel_id>[\w-]+)\.mave\.digital/ep-(?P<episode_code>\d+)'
    _TESTS = [{
        'url': 'https://ochenlichnoe.mave.digital/ep-25',
        'md5': 'aa3e513ef588b4366df1520657cbc10c',
        'info_dict': {
            'id': '4035f587-914b-44b6-aa5a-d76685ad9bc2',
            'ext': 'mp3',
            'display_id': 'ochenlichnoe-25',
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
            'display_id': 'budem-12',
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

    def _real_extract(self, url):
        channel_id, episode_code = self._match_valid_url(url).group(
            'channel_id', 'episode_code')
        display_id = f'{channel_id}-{episode_code}'

        channel_meta = self._load_channel_meta(channel_id, display_id)
        episode_meta = self._load_episode_meta(channel_id, episode_code, display_id)

        return self._create_entry(channel_id, channel_meta, episode_meta)


class MaveChannelIE(MaveBaseIE):
    IE_NAME = 'mave:channel'
    _VALID_URL = r'https?://(?P<id>[\w-]+)\.mave\.digital/?(?:$|[?#])'
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
    }, {
        'url': 'https://geekcity.mave.digital/',
        'info_dict': {
            'id': 'geekcity',
            'title': 'Мужчины в трико',
            'description': 'md5:4164d425d60a0d97abdce9d1f6f8e049',
        },
        'playlist_mincount': 80,
    }]
    _PAGE_SIZE = 50

    def _entries(self, channel_id, channel_meta, page_num):
        page_data = self._download_json(
            f'{self._API_BASE_URL}/{channel_id}/episodes', channel_id, query={
                'view': 'all',
                'page': page_num + 1,
                'sort': 'newest',
                'format': 'all',
            }, note=f'Downloading page {page_num + 1}')
        for ep in traverse_obj(page_data, ('episodes', lambda _, v: v['audio'] and v['id'])):
            yield self._create_entry(channel_id, channel_meta, ep)

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        channel_meta = self._load_channel_meta(channel_id, channel_id)

        return {
            '_type': 'playlist',
            'id': channel_id,
            **traverse_obj(channel_meta, {
                'title': ('title', {str}),
                'description': ('description', {str}),
            }),
            'entries': InAdvancePagedList(
                functools.partial(self._entries, channel_id, channel_meta),
                math.ceil(channel_meta['episodes_count'] / self._PAGE_SIZE), self._PAGE_SIZE),
        }
