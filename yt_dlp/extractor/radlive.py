import json

from ..utils import (
    ExtractorError,
    format_field,
    traverse_obj,
    try_get,
    unified_timestamp
)
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
            'language': 'en',
            'thumbnail': 'https://static.12core.net/cb65ae077a079c68380e38f387fbc438.png',
            'description': '',
            'release_timestamp': 1600185600.0,
            'channel': 'Proximity',
            'channel_id': '9ce6dd01-70a4-4d59-afb6-d01f807cd009',
            'channel_url': 'https://rad.live/content/channel/9ce6dd01-70a4-4d59-afb6-d01f807cd009',
        }
    }, {
        'url': 'https://rad.live/content/episode/bbcf66ec-0d02-4ca0-8dc0-4213eb2429bf',
        'md5': '40b2175f347592125d93e9a344080125',
        'info_dict': {
            'id': 'bbcf66ec-0d02-4ca0-8dc0-4213eb2429bf',
            'ext': 'mp4',
            'title': 'E01: Bad Jokes 1',
            'language': 'en',
            'thumbnail': 'https://lsp.littlstar.com/channels/WHISTLE/BAD_JOKES/SEASON_1/BAD_JOKES_101/poster.jpg',
            'description': 'Bad Jokes - Champions, Adam Pally, Super Troopers, Team Edge and 2Hype',
            'release_timestamp': None,
            'channel': None,
            'channel_id': None,
            'channel_url': None,
            'episode': 'E01: Bad Jokes 1',
            'episode_number': 1,
            'episode_id': '336',
        },
    }]

    def _real_extract(self, url):
        content_type, video_id = self._match_valid_url(url).groups()

        webpage = self._download_webpage(url, video_id)

        content_info = json.loads(self._search_regex(
            r'<script[^>]*type=([\'"])application/json\1[^>]*>(?P<json>{.+?})</script>',
            webpage, 'video info', group='json'))['props']['pageProps']['initialContentData']
        video_info = content_info[content_type]

        if not video_info:
            raise ExtractorError('Unable to extract video info, make sure the URL is valid')

        formats = self._extract_m3u8_formats(video_info['assets']['videos'][0]['url'], video_id)
        self._sort_formats(formats)

        data = video_info.get('structured_data', {})

        release_date = unified_timestamp(traverse_obj(data, ('releasedEvent', 'startDate')))
        channel = next(iter(content_info.get('channels', [])), {})
        channel_id = channel.get('lrn', '').split(':')[-1] or None

        result = {
            'id': video_id,
            'title': video_info['title'],
            'formats': formats,
            'language': traverse_obj(data, ('potentialAction', 'target', 'inLanguage')),
            'thumbnail': traverse_obj(data, ('image', 'contentUrl')),
            'description': data.get('description'),
            'release_timestamp': release_date,
            'channel': channel.get('name'),
            'channel_id': channel_id,
            'channel_url': format_field(channel_id, template='https://rad.live/content/channel/%s'),

        }
        if content_type == 'episode':
            result.update({
                # TODO: Get season number when downloading single episode
                'episode': video_info.get('title'),
                'episode_number': video_info.get('number'),
                'episode_id': video_info.get('id'),
            })

        return result


class RadLiveSeasonIE(RadLiveIE):
    IE_NAME = 'radlive:season'
    _VALID_URL = r'https?://(?:www\.)?rad\.live/content/season/(?P<id>[a-f0-9-]+)'
    _TESTS = [{
        'url': 'https://rad.live/content/season/08a290f7-c9ef-4e22-9105-c255995a2e75',
        'md5': '40b2175f347592125d93e9a344080125',
        'info_dict': {
            'id': '08a290f7-c9ef-4e22-9105-c255995a2e75',
            'title': 'Bad Jokes - Season 1',
        },
        'playlist_mincount': 5,
    }]

    @classmethod
    def suitable(cls, url):
        return False if RadLiveIE.suitable(url) else super(RadLiveSeasonIE, cls).suitable(url)

    def _real_extract(self, url):
        season_id = self._match_id(url)
        webpage = self._download_webpage(url, season_id)

        content_info = json.loads(self._search_regex(
            r'<script[^>]*type=([\'"])application/json\1[^>]*>(?P<json>{.+?})</script>',
            webpage, 'video info', group='json'))['props']['pageProps']['initialContentData']
        video_info = content_info['season']

        entries = [{
            '_type': 'url_transparent',
            'id': episode['structured_data']['url'].split('/')[-1],
            'url': episode['structured_data']['url'],
            'series': try_get(content_info, lambda x: x['series']['title']),
            'season': video_info['title'],
            'season_number': video_info.get('number'),
            'season_id': video_info.get('id'),
            'ie_key': RadLiveIE.ie_key(),
        } for episode in video_info['episodes']]

        return self.playlist_result(entries, season_id, video_info.get('title'))


class RadLiveChannelIE(RadLiveIE):
    IE_NAME = 'radlive:channel'
    _VALID_URL = r'https?://(?:www\.)?rad\.live/content/channel/(?P<id>[a-f0-9-]+)'
    _TESTS = [{
        'url': 'https://rad.live/content/channel/5c4d8df4-6fa0-413c-81e3-873479b49274',
        'md5': '625156a08b7f2b0b849f234e664457ac',
        'info_dict': {
            'id': '5c4d8df4-6fa0-413c-81e3-873479b49274',
            'title': 'Whistle Sports',
        },
        'playlist_mincount': 7,
    }]

    _QUERY = '''
query WebChannelListing ($lrn: ID!) {
  channel (id:$lrn) {
    name
    features {
      structured_data
    }
  }
}'''

    @classmethod
    def suitable(cls, url):
        return False if RadLiveIE.suitable(url) else super(RadLiveChannelIE, cls).suitable(url)

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        graphql = self._download_json(
            'https://content.mhq.12core.net/graphql', channel_id,
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'query': self._QUERY,
                'variables': {'lrn': f'lrn:12core:media:content:channel:{channel_id}'}
            }).encode('utf-8'))

        data = traverse_obj(graphql, ('data', 'channel'))
        if not data:
            raise ExtractorError('Unable to extract video info, make sure the URL is valid')

        entries = [{
            '_type': 'url_transparent',
            'url': feature['structured_data']['url'],
            'ie_key': RadLiveIE.ie_key(),
        } for feature in data['features']]

        return self.playlist_result(entries, channel_id, data.get('name'))
