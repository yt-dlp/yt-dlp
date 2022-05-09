import functools
import json
from .common import InfoExtractor
from ..utils import (
    float_or_none,
    OnDemandPagedList,
    str_or_none,
    str_to_int,
    traverse_obj,
    unified_timestamp
)

_VALID_URL_BASE = r'https?://(?:www\.)?podchaser\.com/podcasts/[\w-]+-'
_API_BASE = 'https://api.podchaser.com'

def _extract_episode(podcast, episode):
    return {
        'id': str(episode.get('id')),
        'title': episode.get('title'),
        'description': episode.get('description'),
        'url': episode.get('audio_url'),
        'thumbnail': episode.get('image_url'),
        'duration': str_to_int(episode.get('length')),
        'timestamp': unified_timestamp(episode.get('air_date')),
        'rating': float_or_none(episode.get('rating')),
        'categories': list(set(traverse_obj(podcast, (('summary', None), 'categories', ..., 'text')))),
        'tags': traverse_obj(podcast, ('tags', ..., 'text')),
        'series': podcast.get('title'),
    }

class PodchaserBaseIE(InfoExtractor):
    pass


class PodchaserIE(PodchaserBaseIE):
    IE_NAME = 'Podchaser'
    _VALID_URL = fr'{_VALID_URL_BASE}(?P<podcast_id>\d+)/episodes/[\w-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.podchaser.com/podcasts/cum-town-36924/episodes/ep-285-freeze-me-off-104365585',
        'info_dict': {
            'id': '104365585',
            'title': 'Ep. 285 – freeze me off',
            'description': 'cam ahn',
            'thumbnail': r're:^https?://.*\.jpg$',
            'ext': 'mp3',
            'categories': ['Comedy'],
            'tags': ['comedy', 'dark humor'],
            'series': 'Cum Town',
            'duration': 3708,
            'timestamp': 1636531259,
            'upload_date': '20211110',
            'rating': 4.0
        }
    }]

    def _real_extract(self, url):
        podcast_id, episode_id = self._match_valid_url(url).group('podcast_id', 'id')
        podcast = self._download_json(f'{_API_BASE}/podcasts/{podcast_id}', podcast_id)
        episode = self._download_json(f'{_API_BASE}/episodes/{episode_id}', episode_id)
        return _extract_episode(podcast, episode)


class PodchaserFeedIE(PodchaserBaseIE):
    IE_NAME = 'Podchaser:feed'
    _VALID_URL = fr'{_VALID_URL_BASE}(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.podchaser.com/podcasts/the-bone-zone-28853',
        'info_dict': {
            'id': '28853',
            'title': 'The Bone Zone',
            'description': 'Podcast by The Bone Zone',
        },
        'playlist_count': 275
    }, {
        'url': 'https://www.podchaser.com/podcasts/sean-carrolls-mindscape-scienc-699349/episodes',
        'info_dict': {
            'id': '699349',
            'title': 'Sean Carroll\'s Mindscape: Science, Society, Philosophy, Culture, Arts, and Ideas',
            'description': 'md5:2cbd8f4749891a84dc8235342e0b5ff1'
        },
        'playlist_mincount': 225
    }]
    _PAGE_SIZE = 100

    @classmethod
    def suitable(cls, url):
        return super().suitable(url) and not PodchaserIE.suitable(url)

    def _fetch_page(self, podcast_id, podcast, page):
        params = {
            'start': page * self._PAGE_SIZE,
            'count': self._PAGE_SIZE,
            'sort_order': 'SORT_ORDER_RECENT',
            'filters': {
                'podcast_id': podcast_id
            },
            'options': {}
        }
        json_response = self._download_json(
            f'{_API_BASE}/list/episode', podcast_id,
            headers={'Content-Type': 'application/json;charset=utf-8'},
            data=json.dumps(params).encode())
        episodes = json_response.get('entities')
        for episode in episodes:
            yield _extract_episode(podcast, episode)

    def _real_extract(self, url):
        podcast_id = self._match_id(url)
        podcast = self._download_json(f'https://api.podchaser.com/podcasts/{podcast_id}', podcast_id)

        entries = OnDemandPagedList(
            functools.partial(self._fetch_page, podcast_id, podcast), _PAGE_SIZE)

        return self.playlist_result(
            entries, str_or_none(podcast.get('id')), podcast.get('title'), podcast.get('description'))
