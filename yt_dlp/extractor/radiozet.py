# coding: utf-8
from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    strip_or_none,
)


class RadioZetPodcastIE(InfoExtractor):
    _VALID_URL = r'https?://player\.radiozet\.pl\/Podcasty/.*?/(?P<id>.+)'
    _TEST = {
        'url': 'https://player.radiozet.pl/Podcasty/Nie-Ma-Za-Co/O-przedmiotach-szkolnych-ktore-przydaja-sie-w-zyciu',
        'md5': 'e03665c316b4fbc5f6a8f232948bbba3',
        'info_dict': {
            'id': '42154',
            'display_id': 'O-przedmiotach-szkolnych-ktore-przydaja-sie-w-zyciu',
            'title': 'O przedmiotach szkolnych, które przydają się w życiu',
            'description': 'md5:fa72bed49da334b09e5b2f79851f185c',
            'release_timestamp': 1592985480,
            'ext': 'mp3',
            'thumbnail': r're:^https?://.*\.png$',
            'duration': 83,
            'series': 'Nie Ma Za Co',
            'creator': 'Katarzyna Pakosińska',
        }
    }

    def _call_api(self, podcast_id, display_id):
        return self._download_json(
            f'https://player.radiozet.pl/api/podcasts/getPodcast/(node)/{podcast_id}/(station)/radiozet',
            display_id)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        podcast_id = self._html_search_regex(r'<div.*?\sid="player".*?\sdata-id=[\'"]([^\'"]+)[\'"]',
                                             webpage, 'podcast id')
        data = self._call_api(podcast_id, display_id)['data'][0]

        return {
            'id': podcast_id,
            'display_id': display_id,
            'title': strip_or_none(data.get('title')),
            'description': strip_or_none(traverse_obj(data, ('program', 'desc'))),
            'release_timestamp': data.get('published_date'),
            'url': traverse_obj(data, ('player', 'stream')),
            'thumbnail': traverse_obj(data, ('program', 'image', 'original')),
            'duration': traverse_obj(data, ('player', 'duration')),
            'series': strip_or_none(traverse_obj(data, ('program', 'title'))),
            'creator': strip_or_none(traverse_obj(data, ('presenter', 0, 'title'))),
        }
