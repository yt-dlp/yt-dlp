# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_podcast_url,
    int_or_none,
    parse_iso8601,
    strip_or_none,
    try_get,
    urlencode_postdata,
)


class SimplecastBaseIE(InfoExtractor):
    _UUID_REGEX = r'[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}'
    _API_BASE = 'https://api.simplecast.com/'

    def _call_api(self, path_tmpl, video_id):
        return self._download_json(
            self._API_BASE + path_tmpl % video_id, video_id)

    def _call_search_api(self, resource, resource_id, resource_url):
        return self._download_json(
            'https://api.simplecast.com/%ss/search' % resource, resource_id,
            data=urlencode_postdata({'url': resource_url}))

    def _parse_episode(self, episode):
        episode_id = episode['id']
        title = episode['title'].strip()
        audio_file = episode.get('audio_file') or {}
        audio_file_url = audio_file.get('url') or episode.get('audio_file_url') or episode['enclosure_url']

        season = episode.get('season') or {}
        season_href = season.get('href')
        season_id = None
        if season_href:
            season_id = self._search_regex(
                r'https?://api.simplecast.com/seasons/(%s)' % self._UUID_REGEX,
                season_href, 'season id', default=None)

        webpage_url = episode.get('episode_url')
        channel_url = None
        if webpage_url:
            channel_url = self._search_regex(
                r'(https?://[^/]+\.simplecast\.com)',
                webpage_url, 'channel url', default=None)

        return {
            'id': episode_id,
            'display_id': episode.get('slug'),
            'title': title,
            'url': clean_podcast_url(audio_file_url),
            'webpage_url': webpage_url,
            'channel_url': channel_url,
            'series': try_get(episode, lambda x: x['podcast']['title']),
            'season_number': int_or_none(season.get('number')),
            'season_id': season_id,
            'thumbnail': episode.get('image_url'),
            'episode_id': episode_id,
            'episode_number': int_or_none(episode.get('number')),
            'description': strip_or_none(episode.get('description')),
            'timestamp': parse_iso8601(episode.get('published_at')),
            'duration': int_or_none(episode.get('duration')),
            'filesize': int_or_none(audio_file.get('size') or episode.get('audio_file_size')),
        }


class SimplecastIE(SimplecastBaseIE):
    IE_NAME = 'simplecast'
    _VALID_URL = r'https?://(?:api\.simplecast\.com/episodes|player\.simplecast\.com)/(?P<id>%s)' % SimplecastBaseIE._UUID_REGEX
    _COMMON_TEST_INFO = {
        'display_id': 'errant-signal-chris-franklin-new-wave-video-essays',
        'id': 'b6dc49a2-9404-4853-9aa9-9cfc097be876',
        'ext': 'mp3',
        'title': 'Errant Signal - Chris Franklin & New Wave Video Essays',
        'episode_number': 1,
        'episode_id': 'b6dc49a2-9404-4853-9aa9-9cfc097be876',
        'description': 'md5:34752789d3d2702e2d2c975fbd14f357',
        'season_number': 1,
        'season_id': 'e23df0da-bae4-4531-8bbf-71364a88dc13',
        'series': 'The RE:BIND.io Podcast',
        'duration': 5343,
        'timestamp': 1580979475,
        'upload_date': '20200206',
        'webpage_url': r're:^https?://the-re-bind-io-podcast\.simplecast\.com/episodes/errant-signal-chris-franklin-new-wave-video-essays',
        'channel_url': r're:^https?://the-re-bind-io-podcast\.simplecast\.com$',
    }
    _TESTS = [{
        'url': 'https://api.simplecast.com/episodes/b6dc49a2-9404-4853-9aa9-9cfc097be876',
        'md5': '8c93be7be54251bf29ee97464eabe61c',
        'info_dict': _COMMON_TEST_INFO,
    }, {
        'url': 'https://player.simplecast.com/b6dc49a2-9404-4853-9aa9-9cfc097be876',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return re.findall(
            r'''(?x)<iframe[^>]+src=["\']
                (
                    https?://(?:embed\.simplecast\.com/[0-9a-f]{8}|
                    player\.simplecast\.com/%s
                ))''' % SimplecastBaseIE._UUID_REGEX, webpage)

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        episode = self._call_api('episodes/%s', episode_id)
        return self._parse_episode(episode)


class SimplecastEpisodeIE(SimplecastBaseIE):
    IE_NAME = 'simplecast:episode'
    _VALID_URL = r'https?://(?!api\.)[^/]+\.simplecast\.com/episodes/(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://the-re-bind-io-podcast.simplecast.com/episodes/errant-signal-chris-franklin-new-wave-video-essays',
        'md5': '8c93be7be54251bf29ee97464eabe61c',
        'info_dict': SimplecastIE._COMMON_TEST_INFO,
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        episode = self._call_search_api(
            'episode', mobj.group(1), mobj.group(0))
        return self._parse_episode(episode)


class SimplecastPodcastIE(SimplecastBaseIE):
    IE_NAME = 'simplecast:podcast'
    _VALID_URL = r'https?://(?!(?:api|cdn|embed|feeds|player)\.)(?P<id>[^/]+)\.simplecast\.com(?!/episodes/[^/?&#]+)'
    _TESTS = [{
        'url': 'https://the-re-bind-io-podcast.simplecast.com',
        'playlist_mincount': 33,
        'info_dict': {
            'id': '07d28d26-7522-42eb-8c53-2bdcfc81c43c',
            'title': 'The RE:BIND.io Podcast',
        },
    }, {
        'url': 'https://the-re-bind-io-podcast.simplecast.com/episodes',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        subdomain = self._match_id(url)
        site = self._call_search_api('site', subdomain, url)
        podcast = site['podcast']
        podcast_id = podcast['id']
        podcast_title = podcast.get('title')

        def entries():
            episodes = self._call_api('podcasts/%s/episodes', podcast_id)
            for episode in (episodes.get('collection') or []):
                info = self._parse_episode(episode)
                info['series'] = podcast_title
                yield info

        return self.playlist_result(entries(), podcast_id, podcast_title)
