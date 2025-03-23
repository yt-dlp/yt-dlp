import functools

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    int_or_none,
    sanitize_url,
    str_or_none,
    traverse_obj,
    unescapeHTML,
    unified_strdate,
)

clean_url = lambda x: unescapeHTML(sanitize_url(x, scheme='https'))


def extract_episode(episode):
    return traverse_obj(episode, {
        'id': ('id', {str_or_none}),
        'ext': 'mp4',
        'timestamp': ('start_at', {unified_strdate}, {int_or_none}),
        'duration': ('tracks', 0, 'length', {int_or_none}),
        'artist': ('tracks', 0, 'display_artist', {str_or_none}),
        'title': ('tracks', 0, 'display_title', {str_or_none}),
        'thumbnail': ('tracks', 0, 'asset_url', {clean_url}),
        'url': ('tracks', 0, 'content', 'assets', 0, 'url', {clean_url}),
        'filesize': ('tracks', 0, 'content', 'assets', 0, 'size', {int_or_none}),
    })


class DIFMShowEpisodeIE(InfoExtractor):
    IE_NAME = 'difm:showepisode'
    _VALID_URL = r'https?://www\.di\.fm/shows/(?P<show_name>[\w-]+)/episodes/(?P<episode_id>\d+)'
    _TESTS = [
        {
            'url': 'https://www.di.fm/shows/airwaves-progressions-radio/episodes/001',
            'md5': '5725ec4226aed05c58b6460df5e4b4df',
            'info_dict': {
                'id': '130151',
                'ext': 'mp4',
                'title': 'Progressions 001 (04 April 2020)',
                'duration': 7456,
                'thumbnail': r're:https?://.*\.jpg',
            },
        }, {
            'url': 'https://www.di.fm/shows/the-global-warm-up/episodes/1095',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        show_name, episode_id = self._match_valid_url(url).group('show_name', 'episode_id')
        video_id = f'{show_name}-{episode_id}'
        webpage = self._download_webpage(url, video_id, fatal=False, impersonate=True)
        json_data = self._search_json('"EpisodeDetail.LayoutEngine",', webpage, 'json_data', video_id)['episode']
        return extract_episode(json_data)


class DIFMShowIE(InfoExtractor):
    IE_NAME = 'difm:show'
    _VALID_URL = r'https?://www\.di\.fm/shows/(?P<show_name>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.di.fm/shows/the-global-warm-up',
        'info_dict': {
            '_type': 'playlist',
            'id': 'the-global-warm-up',
            'title': 'the-global-warm-up',
        },
        'playlist_mincount': 5,
    }]
    _PAGE_SIZE = 5

    def _entries(self, show_name, session_key, page):
        show_metadata = self._download_json(f'https://api.audioaddict.com/v1/di/shows/{show_name}/episodes?page={page + 1}&per_page={self._PAGE_SIZE}', f'{show_name}-{page + 1}', headers={'X-Session-Key': session_key})
        for episode_metadata in show_metadata:
            yield extract_episode(episode_metadata)

    def _real_extract(self, url):
        show_name = self._match_valid_url(url).group('show_name')
        webpage = self._download_webpage(url, show_name, fatal=False, impersonate=True)
        session_key = self._search_json('"user":', webpage, 'json_data', show_name).get('session_key')
        entries = OnDemandPagedList(functools.partial(self._entries, show_name, session_key), self._PAGE_SIZE)
        return self.playlist_result(entries, show_name, show_name)
