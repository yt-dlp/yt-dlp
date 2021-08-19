import json
import re
from datetime import datetime

from .common import InfoExtractor


class RadLiveIE(InfoExtractor):
    IE_NAME = 'radlive'
    _VALID_URL = r'https?://(?:www\.)?rad\.live/content/(?P<content_type>feature|episode)/(?P<id>[a-f0-9-]+)'
    _TESTS = [{
        'url': 'https://rad.live/content/feature/dc5acfbc-761b-4bec-9564-df999905116a',
        'md5': '6219d5d31d52de87d21c9cf5b7cb27ff',
        'info_dict': {
            'id': 'dc5acfbc-761b-4bec-9564-df999905116a',
            'ext': 'mp4',
            'title': 'Deathpact - Digital Mirage 2 [Full Set]',
        }
    }, {
        'url': 'https://rad.live/content/episode/bbcf66ec-0d02-4ca0-8dc0-4213eb2429bf',
        'md5': '40b2175f347592125d93e9a344080125',
        'info_dict': {
            'id': 'bbcf66ec-0d02-4ca0-8dc0-4213eb2429bf',
            'ext': 'mp4',
            'title': 'E01: Bad Jokes 1',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        content_type = re.fullmatch(self._VALID_URL, url).group('content_type')

        _info = json.loads(self._search_regex(
            r'<script[^>]*type=([\'"])application/json\1[^>]*>(?P<json>{.+?})</script>',
            webpage, 'video info', group='json'))['props']['pageProps']['initialContentData']
        info = _info[content_type]

        formats = self._extract_m3u8_formats(info['assets']['videos'][0]['url'], video_id)
        self._sort_formats(formats)

        data = info.get('structured_data', {})

        release_date = data.get('releasedEvent', {}).get('startDate')
        if release_date:
            try:
                release_date = datetime.strptime(release_date, '%Y-%m-%dT%H:%M:%S.%f%z').timestamp()
            except ValueError:
                release_date = None

        channel = next(iter(_info.get('channels', [])), {})
        channel_id = channel.get('lrn', '').split(':')[-1],

        result = {
            'id': video_id,
            'title': info['title'],
            'formats': formats,
            'language': data.get('potentialAction', {}).get('target', {}).get('inLanguage'),
            'thumbnail': data.get('image', {}).get('contentUrl'),
            'description': data.get('description'),
            'release_timestamp': release_date,
            'channel': channel.get('name'),
            'channel_id': channel_id,
            'channel_url': f'https://rad.live/content/channel/{channel_id}' if channel_id else None,

        }
        if content_type == 'episode':
            result.update({
                # TODO: Get season number when downloading single episode
                'episode': info.get('title'),
                'episode_number': info.get('number'),
                'episode_id': info.get('id'),
            })

        return result


class RadLiveSeasonIE(RadLiveIE):
    IE_NAME = 'radlive:season'
    _VALID_URL = r'https?://(?:www\.)?rad\.live/content/season/(?P<id>[a-f0-9-]+)'
    _TESTS = [{
        'url': 'https://rad.live/content/season/08a290f7-c9ef-4e22-9105-c255995a2e75',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if RadLiveIE.suitable(url) else super(RadLiveSeasonIE, cls).suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        _info = json.loads(self._search_regex(
            r'<script[^>]*type=([\'"])application/json\1[^>]*>(?P<json>{.+?})</script>',
            webpage, 'video info', group='json'))['props']['pageProps']['initialContentData']
        info = _info['season']

        entries = []
        for episode in info['episodes']:
            entries.append({
                '_type': 'url_transparent',
                'url': episode['structured_data']['url'],
                'series': next(iter(_info.get('series', [])), {}).get('title'),
                'season': info['title'],
                'season_number': info.get('number'),
                'season_id': info.get('id'),
                'ie_key': RadLiveIE.ie_key(),
            })

        return self.playlist_result(entries, video_id, info['title'])
