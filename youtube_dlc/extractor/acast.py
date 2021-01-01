# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
)


class ACastBaseIE(InfoExtractor):
    def _extract_episode(self, episode, show_info):
        title = episode['title']
        info = {
            'id': episode['id'],
            'display_id': episode.get('episodeUrl'),
            'url': episode['url'],
            'title': title,
            'description': clean_html(episode.get('description') or episode.get('summary')),
            'thumbnail': episode.get('image'),
            'timestamp': parse_iso8601(episode.get('publishDate')),
            'duration': int_or_none(episode.get('duration')),
            'filesize': int_or_none(episode.get('contentLength')),
            'season_number': int_or_none(episode.get('season')),
            'episode': title,
            'episode_number': int_or_none(episode.get('episode')),
        }
        info.update(show_info)
        return info

    def _extract_show_info(self, show):
        return {
            'creator': show.get('author'),
            'series': show.get('title'),
        }

    def _call_api(self, path, video_id, query=None):
        return self._download_json(
            'https://feeder.acast.com/api/v1/shows/' + path, video_id, query=query)


class ACastIE(ACastBaseIE):
    IE_NAME = 'acast'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:(?:embed|www)\.)?acast\.com/|
                            play\.acast\.com/s/
                        )
                        (?P<channel>[^/]+)/(?P<id>[^/#?]+)
                    '''
    _TESTS = [{
        'url': 'https://www.acast.com/sparpodcast/2.raggarmordet-rosterurdetforflutna',
        'md5': 'f5598f3ad1e4776fed12ec1407153e4b',
        'info_dict': {
            'id': '2a92b283-1a75-4ad8-8396-499c641de0d9',
            'ext': 'mp3',
            'title': '2. Raggarmordet - Röster ur det förflutna',
            'description': 'md5:a992ae67f4d98f1c0141598f7bebbf67',
            'timestamp': 1477346700,
            'upload_date': '20161024',
            'duration': 2766,
            'creator': 'Anton Berg & Martin Johnson',
            'series': 'Spår',
            'episode': '2. Raggarmordet - Röster ur det förflutna',
        }
    }, {
        'url': 'http://embed.acast.com/adambuxton/ep.12-adam-joeschristmaspodcast2015',
        'only_matching': True,
    }, {
        'url': 'https://play.acast.com/s/rattegangspodden/s04e09styckmordetihelenelund-del2-2',
        'only_matching': True,
    }, {
        'url': 'https://play.acast.com/s/sparpodcast/2a92b283-1a75-4ad8-8396-499c641de0d9',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel, display_id = re.match(self._VALID_URL, url).groups()
        episode = self._call_api(
            '%s/episodes/%s' % (channel, display_id),
            display_id, {'showInfo': 'true'})
        return self._extract_episode(
            episode, self._extract_show_info(episode.get('show') or {}))


class ACastChannelIE(ACastBaseIE):
    IE_NAME = 'acast:channel'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:www\.)?acast\.com/|
                            play\.acast\.com/s/
                        )
                        (?P<id>[^/#?]+)
                    '''
    _TESTS = [{
        'url': 'https://www.acast.com/todayinfocus',
        'info_dict': {
            'id': '4efc5294-5385-4847-98bd-519799ce5786',
            'title': 'Today in Focus',
            'description': 'md5:c09ce28c91002ce4ffce71d6504abaae',
        },
        'playlist_mincount': 200,
    }, {
        'url': 'http://play.acast.com/s/ft-banking-weekly',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if ACastIE.suitable(url) else super(ACastChannelIE, cls).suitable(url)

    def _real_extract(self, url):
        show_slug = self._match_id(url)
        show = self._call_api(show_slug, show_slug)
        show_info = self._extract_show_info(show)
        entries = []
        for episode in (show.get('episodes') or []):
            entries.append(self._extract_episode(episode, show_info))
        return self.playlist_result(
            entries, show.get('id'), show.get('title'), show.get('description'))
