from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import traverse_obj


class HolodexIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://(?:www\.|staging\.)?holodex\.net/(?:
            api/v2/playlist/(?P<playlist>\d+)|
            watch/(?P<id>[\w-]{11})(?:\?(?:[^#]+&)?playlist=(?P<playlist2>\d+))?
        )'''
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
        'url': 'https://holodex.net/api/v2/playlist/239',
        'info_dict': {
            'id': '239',
            'title': 'Songs/Videos that made fall into the rabbit hole (from my google activity history)',
        },
        'playlist_count': 14,
    }, {
        'url': 'https://holodex.net/watch/_m2mQyaofjI?foo=bar&playlist=69',
        'info_dict': {
            'id': '69',
            'title': '拿著金斧頭的藍髮大姊姊',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://holodex.net/watch/_m2mQyaofjI?playlist=69',
        'info_dict': {
            'id': '_m2mQyaofjI',
            'ext': 'mp4',
            'playable_in_embed': True,
            'like_count': int,
            'uploader': 'Ernst / エンスト',
            'duration': 11,
            'uploader_url': 'http://www.youtube.com/channel/UCqSX4PPZY0cyetqKVY_wRVA',
            'categories': ['Entertainment'],
            'title': '【星街すいせい】星街向你獻上晚安',
            'upload_date': '20210705',
            'description': 'md5:8b8ffb157bae77f2d109021a0b577d4a',
            'channel': 'Ernst / エンスト',
            'channel_id': 'UCqSX4PPZY0cyetqKVY_wRVA',
            'channel_follower_count': int,
            'view_count': int,
            'tags': [],
            'live_status': 'not_live',
            'channel_url': 'https://www.youtube.com/channel/UCqSX4PPZY0cyetqKVY_wRVA',
            'availability': 'public',
            'thumbnail': 'https://i.ytimg.com/vi_webp/_m2mQyaofjI/maxresdefault.webp',
            'age_limit': 0,
            'uploader_id': 'UCqSX4PPZY0cyetqKVY_wRVA',
            'comment_count': int,
        },
        'params': {'noplaylist': True},
    }, {
        'url': 'https://staging.holodex.net/api/v2/playlist/125',
        'only_matching': True,
    }, {
        'url': 'https://staging.holodex.net/watch/rJJTJA_T_b0?playlist=25',
        'only_matching': True,
    }, {
        'url': 'https://staging.holodex.net/watch/s1ifBeukThg',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, playlist_id, pl_id2 = self._match_valid_url(url).group('id', 'playlist', 'playlist2')
        playlist_id = playlist_id or pl_id2

        if not self._yes_playlist(playlist_id, video_id):
            return self.url_result(f'https://www.youtube.com/watch?v={video_id}', YoutubeIE)

        data = self._download_json(f'https://holodex.net/api/v2/playlist/{playlist_id}', playlist_id)
        return self.playlist_from_matches(
            traverse_obj(data, ('videos', ..., 'id')), playlist_id, data.get('name'), ie=YoutubeIE)
