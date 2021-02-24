# coding: utf-8
from __future__ import unicode_literals

import datetime

from .common import InfoExtractor


class NerdCubedFeedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nerdcubed\.co\.uk/feed\.json'
    _TEST = {
        'url': 'http://www.nerdcubed.co.uk/feed.json',
        'info_dict': {
            'id': 'nerdcubed-feed',
            'title': 'nerdcubed.co.uk feed',
        },
        'playlist_mincount': 1300,
    }

    def _real_extract(self, url):
        feed = self._download_json(url, url, 'Downloading NerdCubed JSON feed')

        entries = [{
            '_type': 'url',
            'title': feed_entry['title'],
            'uploader': feed_entry['source']['name'] if feed_entry['source'] else None,
            'upload_date': datetime.datetime.strptime(feed_entry['date'], '%Y-%m-%d').strftime('%Y%m%d'),
            'url': 'http://www.youtube.com/watch?v=' + feed_entry['youtube_id'],
        } for feed_entry in feed]

        return {
            '_type': 'playlist',
            'title': 'nerdcubed.co.uk feed',
            'id': 'nerdcubed-feed',
            'entries': entries,
        }
