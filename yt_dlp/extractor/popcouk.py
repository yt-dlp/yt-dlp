from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    int_or_none,
    traverse_obj,
)


class PopCoUkIE(InfoExtractor):
    _VALID_URL = r'https?://player\.pop\.co\.uk/watch/vod/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://player.pop.co.uk/watch/vod/49724649/the-case-of-the-suspect-sprinkler-the-case-of-the-peculiar-pop-quiz',
        'info_dict': {
            'id': '49724649',
            'ext': 'mp4',
            'title': 'The Case of the Suspect Sprinkler / The Case of the Peculiar Pop Quiz',
            'description': 'md5:688a8e78301b6fec93be1f395f441ba0',
            'series': 'The Inbestigators',
            'series_id': '65ef707f-59f4-11ed-b4c6-0af62ebc70d1',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 6,
            'episode': 'The Case of the Suspect Sprinkler / The Case of the Peculiar Pop Quiz',
            'duration': 1665,
            'age_limit': 0,
            'genres': ['Kids'],
            'thumbnail': r're:https?://thumbnails\.simplestreamcdn\.com/.*\.jpg',
        },
    }]
    _KEY = '8Yd5Ad8Ss8As5Em4Sk8Vs5Wp3Sb7Xr'
    _UK_AGES = {
        'U': 0,
        'PG': 8,
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        show = self._download_json(
            f'https://v6-metadata-cf.simplestreamcdn.com/api/show/{video_id}?key={self._KEY}&cc=GB',
            video_id)['response']['show']

        return self._get_episode(show)

    def _get_episode(self, show):
        video_id = show['id']
        stream = self._download_json(
            f'https://v2-streams-elb.simplestreamcdn.com/api/show/stream/{video_id}?key={self._KEY}&platform=ios',
            video_id)
        fmts, subs = self._extract_m3u8_formats_and_subtitles(stream['response']['stream'], video_id)

        return {
            'id': video_id,
            'formats': fmts,
            'subtitles': subs,
            **traverse_obj(show, {
                'title': 'title',
                'description': 'synopsis',
                'series': 'series_title',
                'series_id': 'series_id',
                'season_number': ('season', {int_or_none}),
                'episode': 'title',
                'episode_number': ('episode', {int_or_none}),
                'duration': ('duration', {int_or_none}),
                'genres': (('genre',),),
                'thumbnail': 'image',
            }),
            'age_limit': self._UK_AGES.get(show['rating']),
        }


class PopCoUkShowIE(PopCoUkIE):
    _VALID_URL = r'https?://player\.pop\.co\.uk/shows/(?P<id>[0-9a-f\-]+)'
    _TESTS = [{
        'url': 'https://player.pop.co.uk/shows/f9863b90-0db7-11ed-b4c6-0af62ebc70d1/swipe-it-with-joe-tasker',
        'info_dict': {
            'id': 'f9863b90-0db7-11ed-b4c6-0af62ebc70d1',
            'title': 'Swipe It With Joe Tasker',
            'description': 'Magazine show sees TV and YouTube star Joe Tasker face a whole host of wacky challenges.',
            'age_limit': 0,
            'thumbnail': r're:https?://thumbnails\.simplestreamcdn\.com/.*\.jpg',
        },
        'playlist_count': 12,
    }]

    def _real_extract(self, url):
        series_id = self._match_id(url)
        series = self._download_json(
            f'https://v6-metadata-cf.simplestreamcdn.com/api/series/{series_id}?key={self._KEY}&cc=GB',
            series_id)['response']['series']

        def get_entries(seasons):
            for season in seasons:
                for tile in season.get('tiles', []):
                    yield self._get_episode(tile)

        return {
            '_type': 'playlist',
            'id': series_id,
            **traverse_obj(series, {
                'title': 'title',
                'description': 'synopsis',
                'thumbnail': 'image',
            }),
            'age_limit': self._UK_AGES.get(series['rating']),
            'entries': get_entries(series.get('seasons', [])),
        }
