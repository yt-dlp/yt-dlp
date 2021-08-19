# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    clean_podcast_url,
    int_or_none,
    parse_iso8601,
    try_get,
)


class ApplePodcastsIE(InfoExtractor):
    _VALID_URL = r'https?://podcasts\.apple\.com/(?:[^/]+/)?podcast(?:/[^/]+){1,2}.*?\bi=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://podcasts.apple.com/us/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'md5': 'df02e6acb11c10e844946a39e7222b08',
        'info_dict': {
            'id': '1000482637777',
            'ext': 'mp3',
            'title': '207 - Whitney Webb Returns',
            'description': 'md5:13a73bade02d2e43737751e3987e1399',
            'upload_date': '20200705',
            'timestamp': 1593921600,
            'duration': 6425,
            'series': 'The Tim Dillon Show',
        }
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/id1135137367?i=1000482637777',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        ember_data = self._parse_json(self._search_regex(
            r'id="shoebox-ember-data-store"[^>]*>\s*({.+?})\s*<',
            webpage, 'ember data'), episode_id)
        ember_data = ember_data.get(episode_id) or ember_data
        episode = ember_data['data']['attributes']
        description = episode.get('description') or {}

        series = None
        for inc in (ember_data.get('included') or []):
            if inc.get('type') == 'media/podcast':
                series = try_get(inc, lambda x: x['attributes']['name'])

        return {
            'id': episode_id,
            'title': episode['name'],
            'url': clean_podcast_url(episode['assetUrl']),
            'description': description.get('standard') or description.get('short'),
            'timestamp': parse_iso8601(episode.get('releaseDateTime')),
            'duration': int_or_none(episode.get('durationInMilliseconds'), 1000),
            'series': series,
        }
