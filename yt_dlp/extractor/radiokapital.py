from .common import InfoExtractor
from ..utils import (
    clean_html,
    traverse_obj,
    unescapeHTML,
)

import itertools
from urllib.parse import urlencode


class RadioKapitalBaseIE(InfoExtractor):
    def _call_api(self, resource, video_id, note='Downloading JSON metadata', qs={}):
        return self._download_json(
            f'https://www.radiokapital.pl/wp-json/kapital/v1/{resource}?{urlencode(qs)}',
            video_id, note=note)

    def _parse_episode(self, data):
        release = '%s%s%s' % (data['published'][6:11], data['published'][3:6], data['published'][:3])
        return {
            '_type': 'url_transparent',
            'url': data['mixcloud_url'],
            'ie_key': 'Mixcloud',
            'title': unescapeHTML(data['title']),
            'description': clean_html(data.get('content')),
            'tags': traverse_obj(data, ('tags', ..., 'name')),
            'release_date': release,
            'series': traverse_obj(data, ('show', 'title')),
        }


class RadioKapitalIE(RadioKapitalBaseIE):
    IE_NAME = 'radiokapital'
    _VALID_URL = r'https?://(?:www\.)?radiokapital\.pl/shows/[a-z\d-]+/(?P<id>[a-z\d-]+)'

    _TESTS = [{
        'url': 'https://radiokapital.pl/shows/tutaj-sa-smoki/5-its-okay-to-be-immaterial',
        'info_dict': {
            'id': 'radiokapital_radio-kapitał-tutaj-są-smoki-5-its-okay-to-be-immaterial-2021-05-20',
            'ext': 'm4a',
            'title': '#5: It’s okay to\xa0be\xa0immaterial',
            'description': 'md5:2499da5fbfb0e88333b7d37ec8e9e4c4',
            'uploader': 'Radio Kapitał',
            'uploader_id': 'radiokapital',
            'timestamp': 1621640164,
            'upload_date': '20210521',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        episode = self._call_api('episodes/%s' % video_id, video_id)
        return self._parse_episode(episode)


class RadioKapitalShowIE(RadioKapitalBaseIE):
    IE_NAME = 'radiokapital:show'
    _VALID_URL = r'https?://(?:www\.)?radiokapital\.pl/shows/(?P<id>[a-z\d-]+)/?(?:$|[?#])'

    _TESTS = [{
        'url': 'https://radiokapital.pl/shows/wesz',
        'info_dict': {
            'id': '100',
            'title': 'WĘSZ',
            'description': 'md5:3a557a1e0f31af612b0dcc85b1e0ca5c',
        },
        'playlist_mincount': 17,
    }]

    def _get_episode_list(self, series_id, page_no):
        return self._call_api(
            'episodes', series_id,
            f'Downloading episode list page #{page_no}', qs={
                'show': series_id,
                'page': page_no,
            })

    def _entries(self, series_id):
        for page_no in itertools.count(1):
            episode_list = self._get_episode_list(series_id, page_no)
            yield from (self._parse_episode(ep) for ep in episode_list['items'])
            if episode_list['next'] is None:
                break

    def _real_extract(self, url):
        series_id = self._match_id(url)

        show = self._call_api(f'shows/{series_id}', series_id, 'Downloading show metadata')
        entries = self._entries(series_id)
        return {
            '_type': 'playlist',
            'entries': entries,
            'id': str(show['id']),
            'title': show.get('title'),
            'description': clean_html(show.get('content')),
        }
