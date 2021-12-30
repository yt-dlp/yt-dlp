from __future__ import unicode_literals

from .common import InfoExtractor


class BitwaveReplayIE(InfoExtractor):
    IE_NAME = 'bitwave:replay'
    _VALID_URL = r'https?://(?:www\.)?bitwave\.tv/(?P<user>\w+)/replay/(?P<id>\w+)/?$'
    _TEST = {
        'url': 'https://bitwave.tv/RhythmicCarnage/replay/z4P6eq5L7WDrM85UCrVr',
        'only_matching': True
    }

    def _real_extract(self, url):
        replay_id = self._match_id(url)
        replay = self._download_json(
            'https://api.bitwave.tv/v1/replays/' + replay_id,
            replay_id
        )

        return {
            'id': replay_id,
            'title': replay['data']['title'],
            'uploader': replay['data']['name'],
            'uploader_id': replay['data']['name'],
            'url': replay['data']['url'],
            'thumbnails': [
                {'url': x} for x in replay['data']['thumbnails']
            ],
        }


class BitwaveStreamIE(InfoExtractor):
    IE_NAME = 'bitwave:stream'
    _VALID_URL = r'https?://(?:www\.)?bitwave\.tv/(?P<id>\w+)/?$'
    _TEST = {
        'url': 'https://bitwave.tv/doomtube',
        'only_matching': True
    }

    def _real_extract(self, url):
        username = self._match_id(url)
        channel = self._download_json(
            'https://api.bitwave.tv/v1/channels/' + username,
            username)

        formats = self._extract_m3u8_formats(
            channel['data']['url'], username,
            'mp4')
        self._sort_formats(formats)

        return {
            'id': username,
            'title': channel['data']['title'],
            'uploader': username,
            'uploader_id': username,
            'formats': formats,
            'thumbnail': channel['data']['thumbnail'],
            'is_live': True,
            'view_count': channel['data']['viewCount']
        }
