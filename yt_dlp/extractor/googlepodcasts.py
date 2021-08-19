# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    clean_podcast_url,
    int_or_none,
    try_get,
    urlencode_postdata,
)


class GooglePodcastsBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://podcasts\.google\.com/feed/'

    def _batch_execute(self, func_id, video_id, params):
        return json.loads(self._download_json(
            'https://podcasts.google.com/_/PodcastsUi/data/batchexecute',
            video_id, data=urlencode_postdata({
                'f.req': json.dumps([[[func_id, json.dumps(params), None, '1']]]),
            }), transform_source=lambda x: self._search_regex(r'(?s)(\[.+\])', x, 'data'))[0][2])

    def _extract_episode(self, episode):
        return {
            'id': episode[4][3],
            'title': episode[8],
            'url': clean_podcast_url(episode[13]),
            'thumbnail': episode[2],
            'description': episode[9],
            'creator': try_get(episode, lambda x: x[14]),
            'timestamp': int_or_none(episode[11]),
            'duration': int_or_none(episode[12]),
            'series': episode[1],
        }


class GooglePodcastsIE(GooglePodcastsBaseIE):
    IE_NAME = 'google:podcasts'
    _VALID_URL = GooglePodcastsBaseIE._VALID_URL_BASE + r'(?P<feed_url>[^/]+)/episode/(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://podcasts.google.com/feed/aHR0cHM6Ly9mZWVkcy5ucHIub3JnLzM0NDA5ODUzOS9wb2RjYXN0LnhtbA/episode/MzBlNWRlN2UtOWE4Yy00ODcwLTk2M2MtM2JlMmUyNmViOTRh',
        'md5': 'fa56b2ee8bd0703e27e42d4b104c4766',
        'info_dict': {
            'id': '30e5de7e-9a8c-4870-963c-3be2e26eb94a',
            'ext': 'mp3',
            'title': 'WWDTM New Year 2021',
            'description': 'We say goodbye to 2020 with Christine Baranksi, Doug Jones, Jonna Mendez, and Kellee Edwards.',
            'upload_date': '20210102',
            'timestamp': 1609606800,
            'duration': 2901,
            'series': "Wait Wait... Don't Tell Me!",
        }
    }

    def _real_extract(self, url):
        b64_feed_url, b64_guid = self._match_valid_url(url).groups()
        episode = self._batch_execute(
            'oNjqVe', b64_guid, [b64_feed_url, b64_guid])[1]
        return self._extract_episode(episode)


class GooglePodcastsFeedIE(GooglePodcastsBaseIE):
    IE_NAME = 'google:podcasts:feed'
    _VALID_URL = GooglePodcastsBaseIE._VALID_URL_BASE + r'(?P<id>[^/?&#]+)/?(?:[?#&]|$)'
    _TEST = {
        'url': 'https://podcasts.google.com/feed/aHR0cHM6Ly9mZWVkcy5ucHIub3JnLzM0NDA5ODUzOS9wb2RjYXN0LnhtbA',
        'info_dict': {
            'title': "Wait Wait... Don't Tell Me!",
            'description': "NPR's weekly current events quiz. Have a laugh and test your news knowledge while figuring out what's real and what we've made up.",
        },
        'playlist_mincount': 20,
    }

    def _real_extract(self, url):
        b64_feed_url = self._match_id(url)
        data = self._batch_execute('ncqJEe', b64_feed_url, [b64_feed_url])

        entries = []
        for episode in (try_get(data, lambda x: x[1][0]) or []):
            entries.append(self._extract_episode(episode))

        feed = try_get(data, lambda x: x[3]) or []
        return self.playlist_result(
            entries, playlist_title=try_get(feed, lambda x: x[0]),
            playlist_description=try_get(feed, lambda x: x[2]))
