from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import traverse_obj


class HolodexIE(InfoExtractor):
    _VALID_URL = r'^(?!.*?playlist)https?://(?:www\.|staging\.)?holodex\.net/watch/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://holodex.net/watch/9kQ2GtvDV3s',
        'md5': 'be5ffce2f0feae8ba4c01553abc0f175',
        'info_dict': {
            'ext': 'mp4',
            'id': '9kQ2GtvDV3s',
            'title': '【おちゃめ機能】ホロライブが吹っ切れた【24人で歌ってみた】',
            'channel_id': 'UCJFZiqLMntJufDCHc6bQixg',
            'playable_in_embed': True,
            'tags': 'count:43',
            'age_limit': 0,
            'live_status': 'not_live',
            'description': 'md5:040e866c09dc4ab899b36479f4b7c7a2',
            'channel_url': 'https://www.youtube.com/channel/UCJFZiqLMntJufDCHc6bQixg',
            'upload_date': '20200406',
            'uploader_url': 'http://www.youtube.com/channel/UCJFZiqLMntJufDCHc6bQixg',
            'view_count': int,
            'channel': 'hololive ホロライブ - VTuber Group',
            'categories': ['Music'],
            'uploader': 'hololive ホロライブ - VTuber Group',
            'channel_follower_count': int,
            'uploader_id': 'UCJFZiqLMntJufDCHc6bQixg',
            'availability': 'public',
            'thumbnail': 'https://i.ytimg.com/vi_webp/9kQ2GtvDV3s/maxresdefault.webp',
            'duration': 263,
            'like_count': int,
        },
    }, {
        'url': 'https://staging.holodex.net/watch/s1ifBeukThg',
        'only_matching': True,
    }, ]

    def _real_extract(self, url):
        return self.url_result(f'https://www.youtube.com/watch?v={self._match_id(url)}', YoutubeIE)


class HolodexPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|staging\.)?holodex\.net/(?:watch/.*?playlist=|api/v2/playlist/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://holodex.net/api/v2/playlist/239',
        'info_dict': {
            'id': '239',
            'title': 'Songs/Videos that made fall into the rabbit hole (from my google activity history)',
        },
        'playlist_count': 14,
    }, {
        'url': 'https://holodex.net/watch/_m2mQyaofjI?playlist=69',
        'info_dict': {
            'id': '69',
            'title': '拿著金斧頭的藍髮大姊姊'
        },
        'playlist_count': 3,
    }, {
        'url': 'https://staging.holodex.net/api/v2/playlist/125',
        'only_matching': True,
    }, {
        'url': 'https://staging.holodex.net/watch/rJJTJA_T_b0?playlist=25',
        'only_matching': True,
    },
    ]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        data = self._download_json(f'https://holodex.net/api/v2/playlist/{playlist_id}', playlist_id)
        return self.playlist_from_matches(
            traverse_obj(data, ('videos', ..., 'id')), playlist_id, data.get('name'), ie=YoutubeIE)
