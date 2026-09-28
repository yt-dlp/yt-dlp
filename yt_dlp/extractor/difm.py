import functools

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    int_or_none,
    sanitize_url,
    str_or_none,
    traverse_obj,
    unescapeHTML,
    unified_timestamp,
)

clean_url = lambda x: unescapeHTML(sanitize_url(x, scheme='https'))


class DIFMShowEpisodeIE(InfoExtractor):
    IE_NAME = 'difm:showepisode'
    _VALID_URL = r'https?://www\.di\.fm/shows/(?P<show_id>[\w-]+)/episodes/(?P<episode_id>[\w-]+)'
    _TESTS = [
        {
            'url': 'https://www.di.fm/shows/airwaves-progressions-radio/episodes/001',
            'md5': '5725ec4226aed05c58b6460df5e4b4df',
            'info_dict': {
                'id': '130151',
                'ext': 'm4a',
                'title': 'Progressions 001 (04 April 2020)',
                'description': '',
                'duration': 7456,
                'thumbnail': r're:https?://.*\.jpg',
                'upload_date': '20200404',
                'timestamp': 1586008800,
                'artists': ['Airwave'],
                'filesize': 120584191,
                'like_count': int,
                'dislike_count': int,
            },
        }, {
            'url': 'https://www.di.fm/shows/the-global-warm-up/episodes/1095',
            'only_matching': True,
        },
    ]

    def _extract_data(self, episode):
        return {
            'ext': 'm4a',
            **traverse_obj(episode, {
                'id': ('id', {str_or_none}),
                'timestamp': ('start_at', {unified_timestamp}),
                'description': ('description', {str}),
                'duration': ('tracks', 0, 'length', {int_or_none}),
                'artist': ('tracks', 0, 'display_artist', {str}),
                'title': ('tracks', 0, 'display_title', {str}),
                'like_count': ('tracks', 0, 'votes', 'up', {int_or_none}),
                'dislike_count': ('tracks', 0, 'votes', 'down', {int_or_none}),
                'thumbnail': ('tracks', 0, 'asset_url', {clean_url}),
                'url': ('tracks', 0, 'content', 'assets', 0, 'url', {clean_url}),
                'filesize': ('tracks', 0, 'content', 'assets', 0, 'size', {int_or_none}),
            }),
        }

    def _real_extract(self, url):
        show_id, episode_id = self._match_valid_url(url).group('show_id', 'episode_id')
        video_id = f'{show_id}-{episode_id}'
        webpage = self._download_webpage(url, video_id, fatal=True, impersonate=True)
        json_data = self._search_json('"EpisodeDetail.LayoutEngine",', webpage, 'json_data', video_id)['episode']
        return self._extract_data(json_data)


class DIFMShowIE(DIFMShowEpisodeIE):
    IE_NAME = 'difm:show'
    _VALID_URL = r'https?://www\.di\.fm/shows/(?P<id>[\w-]+)$'
    _TESTS = [{
        'url': 'https://www.di.fm/shows/the-global-warm-up',
        'info_dict': {
            '_type': 'playlist',
            'id': 'the-global-warm-up',
            'title': 'The Global Warm Up with Judge Jules',
        },
        'playlist_mincount': 5,
    }]
    _PAGE_SIZE = 5

    def _entries(self, show_id, session_key, page):
        show_metadata = self._download_json(
            f'https://api.audioaddict.com/v1/di/shows/{show_id}/episodes',
            f'{show_id}-{page + 1}', headers={'X-Session-Key': session_key},
            query={'page': str(page + 1), 'per_page': str(self._PAGE_SIZE)},
        )
        for episode_metadata in show_metadata:
            yield self._extract_data(episode_metadata)

    def _real_extract(self, url):
        show_id = self._match_id(url)
        webpage = self._download_webpage(url, show_id, fatal=True, impersonate=True)
        show_title = self._html_extract_title(webpage).removesuffix(' - DI.FM')
        session_key = self._search_regex(r'"session_key"\s*:\s*"(?P<session_key>\w+)"', webpage, 'session_key')
        entries = OnDemandPagedList(functools.partial(self._entries, show_id, session_key), self._PAGE_SIZE)
        return self.playlist_result(entries, show_id, show_title)
