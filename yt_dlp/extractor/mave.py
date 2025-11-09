from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
)


class MaveBaseIE(InfoExtractor):
    _API_BASE_URL = 'https://api.mave.digital/v1/website'
    _API_BASE_STORAGE_URL = 'https://store.cloud.mts.ru/mave/'

    def _load_channel_meta(self, channel_id):
        return self._download_json(
            f'{self._API_BASE_URL}/{channel_id}/', channel_id,
            note='Downloading channel metadata')

    def _load_episode_meta(self, channel_id, episode_code):
        return self._download_json(
            f'{self._API_BASE_URL}/{channel_id}/episodes/{episode_code}',
            episode_code)

    def _create_entry(self, channel_id, channel_meta, episode_meta):
        display_id = f'{channel_id}-{episode_meta["code"]}'

        reactions = episode_meta.get('reactions')

        return {
            'display_id': display_id,
            'channel_id': channel_id,
            'channel_url': f'https://{channel_id}.mave.digital/',
            'vcodec': 'none',
            'thumbnail': self._API_BASE_STORAGE_URL + episode_meta['image'],
            'url': self._API_BASE_STORAGE_URL + episode_meta['audio'],
            'id': episode_meta['id'],
            'title': episode_meta['title'],
            'description': clean_html(episode_meta['description']),
            'duration': int_or_none(episode_meta['duration']),
            'season_number': int_or_none(episode_meta['season']),
            'episode_number': int_or_none(episode_meta['number']),
            'view_count': int_or_none(episode_meta['listenings']),
            'like_count': next(
                (int(r['count']) for r in reactions
                 if r['type'] == 'like'),
                0,
            ) if reactions else None,
            'dislike_count': next(
                (int(r['count']) for r in reactions
                 if r['type'] == 'dislike'),
                0,
            ) if reactions else None,
            'age_limit': 18 if episode_meta.get('is_explicit') else None,
            'timestamp': parse_iso8601(episode_meta['publish_date']),
            'series_id': channel_meta['podcast']['id'],
            'series': channel_meta['podcast']['title'],
            'channel': channel_meta['podcast']['title'],
            'uploader': channel_meta['podcast']['author'],
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

        channel_meta = self._load_channel_meta(channel_id)
        episode_meta = self._load_episode_meta(channel_id, episode_code)

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

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        channel_meta = self._load_channel_meta(channel_id)

        entries = []
        page = 1

        while True:
            data = self._download_json(
                f'{self._API_BASE_URL}/{channel_id}/episodes?'
                f'view=all&page={page}&sort=newest&format=all',
                channel_id)

            episodes = data.get('episodes', [])

            if not episodes:
                break
            else:
                for episode_meta in data['episodes']:
                    entries.append(self._create_entry(
                        channel_id, channel_meta, episode_meta))

                page += 1

        return {
            '_type': 'playlist',
            'id': channel_id,
            'title': channel_meta['podcast']['title'],
            'description': channel_meta['podcast']['description'],
            'entries': entries[::-1],
        }
