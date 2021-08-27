# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
)


class ToonGogglesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?toongoggles\.com/shows/(?P<show_id>\d+)(?:/[^/]+/episodes/(?P<episode_id>\d+))?'
    _TESTS = [{
        'url': 'http://www.toongoggles.com/shows/217143/bernard-season-2/episodes/217147/football',
        'md5': '18289fc2b951eff6b953a9d8f01e6831',
        'info_dict': {
            'id': '217147',
            'ext': 'mp4',
            'title': 'Football',
            'uploader_id': '1',
            'description': 'Bernard decides to play football in order to be better than Lloyd and tries to beat him no matter how, he even cheats.',
            'upload_date': '20160718',
            'timestamp': 1468879330,
        }
    }, {
        'url': 'http://www.toongoggles.com/shows/227759/om-nom-stories-around-the-world',
        'info_dict': {
            'id': '227759',
            'title': 'Om Nom Stories Around The World',
        },
        'playlist_mincount': 11,
    }]

    def _call_api(self, action, page_id, query):
        query.update({
            'for_ng': 1,
            'for_web': 1,
            'show_meta': 1,
            'version': 7.0,
        })
        return self._download_json('http://api.toongoggles.com/' + action, page_id, query=query)

    def _parse_episode_data(self, episode_data):
        title = episode_data['episode_name']

        return {
            '_type': 'url_transparent',
            'id': episode_data['episode_id'],
            'title': title,
            'url': 'kaltura:513551:' + episode_data['entry_id'],
            'thumbnail': episode_data.get('thumbnail_url'),
            'description': episode_data.get('description'),
            'duration': parse_duration(episode_data.get('hms')),
            'series': episode_data.get('show_name'),
            'season_number': int_or_none(episode_data.get('season_num')),
            'episode_id': episode_data.get('episode_id'),
            'episode': title,
            'episode_number': int_or_none(episode_data.get('episode_num')),
            'categories': episode_data.get('categories'),
            'ie_key': 'Kaltura',
        }

    def _real_extract(self, url):
        show_id, episode_id = self._match_valid_url(url).groups()
        if episode_id:
            episode_data = self._call_api('search', episode_id, {
                'filter': 'episode',
                'id': episode_id,
            })['objects'][0]
            return self._parse_episode_data(episode_data)
        else:
            show_data = self._call_api('getepisodesbyshow', show_id, {
                'max': 1000000000,
                'showid': show_id,
            })
            entries = []
            for episode_data in show_data.get('objects', []):
                entries.append(self._parse_episode_data(episode_data))
            return self.playlist_result(entries, show_id, show_data.get('show_name'))
