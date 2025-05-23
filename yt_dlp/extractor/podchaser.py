import functools
import json

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    float_or_none,
    int_or_none,
    orderedSet,
    str_or_none,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class PodchaserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?podchaser\.com/podcasts/[\w-]+-(?P<podcast_id>\d+)(?:/episodes/[\w-]+-(?P<id>\d+))?'
    _PAGE_SIZE = 100
    _TESTS = [{
        'url': 'https://www.podchaser.com/podcasts/cum-town-36924/episodes/ep-285-freeze-me-off-104365585',
        'info_dict': {
            'id': '104365585',
            'title': 'Ep. 285 – freeze me off',
            'description': 'cam ahn',
            'thumbnail': r're:https?://.+/.+\.jpg',
            'ext': 'mp3',
            'categories': ['Comedy', 'News', 'Politics', 'Arts'],
            'tags': ['comedy', 'dark humor'],
            'series': 'The Adam Friedland Show Podcast',
            'duration': 3708,
            'timestamp': 1636531259,
            'upload_date': '20211110',
            'average_rating': 4.0,
            'series_id': '36924',
        },
    }, {
        'url': 'https://www.podchaser.com/podcasts/the-bone-zone-28853',
        'info_dict': {
            'id': '28853',
            'title': 'The Bone Zone',
            'description': r're:The official home of the Bone Zone podcast.+',
        },
        'playlist_mincount': 275,
    }, {
        'url': 'https://www.podchaser.com/podcasts/sean-carrolls-mindscape-scienc-699349/episodes',
        'info_dict': {
            'id': '699349',
            'title': 'Sean Carroll\'s Mindscape: Science, Society, Philosophy, Culture, Arts, and Ideas',
            'description': 'md5:2cbd8f4749891a84dc8235342e0b5ff1',
        },
        'playlist_mincount': 225,
    }]

    @staticmethod
    def _parse_episode(episode, podcast):
        info = traverse_obj(episode, {
            'id': ('id', {int}, {str_or_none}, {require('episode ID')}),
            'title': ('title', {str}),
            'description': ('description', {str}),
            'url': ('audio_url', {url_or_none}),
            'thumbnail': ('image_url', {url_or_none}),
            'duration': ('length', {int_or_none}),
            'timestamp': ('air_date', {unified_timestamp}),
            'average_rating': ('rating', {float_or_none}),
        })
        info.update(traverse_obj(podcast, {
            'series': ('title', {str}),
            'series_id': ('id', {int}, {str_or_none}),
            'categories': (('summary', None), 'categories', ..., 'text', {str}, filter, all, {orderedSet}),
            'tags': ('tags', ..., 'text', {str}),
        }))
        info['vcodec'] = 'none'

        if info.get('series_id'):
            podcast_slug = traverse_obj(podcast, ('slug', {str})) or 'podcast'
            episode_slug = traverse_obj(episode, ('slug', {str})) or 'episode'
            info['webpage_url'] = '/'.join((
                'https://www.podchaser.com/podcasts',
                '-'.join((podcast_slug[:30].rstrip('-'), info['series_id'])),
                '-'.join((episode_slug[:30].rstrip('-'), info['id']))))

        return info

    def _call_api(self, path, *args, **kwargs):
        return self._download_json(f'https://api.podchaser.com/{path}', *args, **kwargs)

    def _fetch_page(self, podcast_id, podcast, page):
        json_response = self._call_api(
            'list/episode', podcast_id,
            headers={'Content-Type': 'application/json;charset=utf-8'},
            data=json.dumps({
                'start': page * self._PAGE_SIZE,
                'count': self._PAGE_SIZE,
                'sort_order': 'SORT_ORDER_RECENT',
                'filters': {
                    'podcast_id': podcast_id,
                },
                'options': {},
            }).encode())

        for episode in json_response['entities']:
            yield self._parse_episode(episode, podcast)

    def _real_extract(self, url):
        podcast_id, episode_id = self._match_valid_url(url).group('podcast_id', 'id')
        podcast = self._call_api(f'podcasts/{podcast_id}', episode_id or podcast_id)
        if not episode_id:
            return self.playlist_result(
                OnDemandPagedList(functools.partial(self._fetch_page, podcast_id, podcast), self._PAGE_SIZE),
                str_or_none(podcast.get('id')), podcast.get('title'), podcast.get('description'))

        episode = self._call_api(f'podcasts/{podcast_id}/episodes/{episode_id}/player_ids', episode_id)
        return self._parse_episode(episode, podcast)
