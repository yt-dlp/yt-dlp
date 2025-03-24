import base64
import urllib.parse

from ._base import YoutubeBaseInfoExtractor
from ._tab import YoutubeTabIE
from ...utils import ExtractorError, classproperty, parse_qs, update_url_query, url_or_none


class YoutubeYtBeIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'youtu.be'
    _VALID_URL = rf'https?://youtu\.be/(?P<id>[0-9A-Za-z_-]{{11}})/*?.*?\blist=(?P<playlist_id>{YoutubeBaseInfoExtractor._PLAYLIST_ID_RE})'
    _TESTS = [{
        'url': 'https://youtu.be/yeWKywCrFtk?list=PL2qgrgXsNUG5ig9cat4ohreBjYLAPC0J5',
        'info_dict': {
            'id': 'yeWKywCrFtk',
            'ext': 'mp4',
            'title': 'Small Scale Baler and Braiding Rugs',
            'uploader': 'Backus-Page House Museum',
            'uploader_id': '@backuspagemuseum',
            'uploader_url': r're:https?://(?:www\.)?youtube\.com/@backuspagemuseum',
            'upload_date': '20161008',
            'description': 'md5:800c0c78d5eb128500bffd4f0b4f2e8a',
            'categories': ['Nonprofits & Activism'],
            'tags': list,
            'like_count': int,
            'age_limit': 0,
            'playable_in_embed': True,
            'thumbnail': r're:^https?://.*\.webp',
            'channel': 'Backus-Page House Museum',
            'channel_id': 'UCEfMCQ9bs3tjvjy1s451zaw',
            'live_status': 'not_live',
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCEfMCQ9bs3tjvjy1s451zaw',
            'availability': 'public',
            'duration': 59,
            'comment_count': int,
            'channel_follower_count': int,
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        },
    }, {
        'url': 'https://youtu.be/uWyaPkt-VOI?list=PL9D9FC436B881BA21',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        playlist_id = mobj.group('playlist_id')
        return self.url_result(
            update_url_query('https://www.youtube.com/watch', {
                'v': video_id,
                'list': playlist_id,
                'feature': 'youtu.be',
            }), ie=YoutubeTabIE.ie_key(), video_id=playlist_id)


class YoutubeLivestreamEmbedIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube livestream embeds'
    _VALID_URL = r'https?://(?:\w+\.)?youtube\.com/embed/live_stream/?\?(?:[^#]+&)?channel=(?P<id>[^&#]+)'
    _TESTS = [{
        'url': 'https://www.youtube.com/embed/live_stream?channel=UC2_KI6RB__jGdlnK6dvFEZA',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        return self.url_result(
            f'https://www.youtube.com/channel/{channel_id}/live',
            ie=YoutubeTabIE.ie_key(), video_id=channel_id)


class YoutubeYtUserIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube user videos; "ytuser:" prefix'
    IE_NAME = 'youtube:user'
    _VALID_URL = r'ytuser:(?P<id>.+)'
    _TESTS = [{
        'url': 'ytuser:phihag',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        return self.url_result(f'https://www.youtube.com/user/{user_id}', YoutubeTabIE, user_id)


class YoutubeFavouritesIE(YoutubeBaseInfoExtractor):
    IE_NAME = 'youtube:favorites'
    IE_DESC = 'YouTube liked videos; ":ytfav" keyword (requires cookies)'
    _VALID_URL = r':ytfav(?:ou?rite)?s?'
    _LOGIN_REQUIRED = True
    _TESTS = [{
        'url': ':ytfav',
        'only_matching': True,
    }, {
        'url': ':ytfavorites',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(
            'https://www.youtube.com/playlist?list=LL',
            ie=YoutubeTabIE.ie_key())


class YoutubeFeedsInfoExtractor(YoutubeBaseInfoExtractor):
    """
    Base class for feed extractors
    Subclasses must re-define the _FEED_NAME property.
    """
    _LOGIN_REQUIRED = True
    _FEED_NAME = 'feeds'

    @classproperty
    def IE_NAME(cls):
        return f'youtube:{cls._FEED_NAME}'

    def _real_extract(self, url):
        return self.url_result(
            f'https://www.youtube.com/feed/{self._FEED_NAME}', ie=YoutubeTabIE.ie_key())


class YoutubeWatchLaterIE(YoutubeBaseInfoExtractor):
    IE_NAME = 'youtube:watchlater'
    IE_DESC = 'Youtube watch later list; ":ytwatchlater" keyword (requires cookies)'
    _VALID_URL = r':ytwatchlater'
    _TESTS = [{
        'url': ':ytwatchlater',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(
            'https://www.youtube.com/playlist?list=WL', ie=YoutubeTabIE.ie_key())


class YoutubeRecommendedIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'YouTube recommended videos; ":ytrec" keyword'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/?(?:[?#]|$)|:ytrec(?:ommended)?'
    _FEED_NAME = 'recommended'
    _LOGIN_REQUIRED = False
    _TESTS = [{
        'url': ':ytrec',
        'only_matching': True,
    }, {
        'url': ':ytrecommended',
        'only_matching': True,
    }, {
        'url': 'https://youtube.com',
        'only_matching': True,
    }]


class YoutubeSubscriptionsIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'YouTube subscriptions feed; ":ytsubs" keyword (requires cookies)'
    _VALID_URL = r':ytsub(?:scription)?s?'
    _FEED_NAME = 'subscriptions'
    _TESTS = [{
        'url': ':ytsubs',
        'only_matching': True,
    }, {
        'url': ':ytsubscriptions',
        'only_matching': True,
    }]


class YoutubeHistoryIE(YoutubeFeedsInfoExtractor):
    IE_DESC = 'Youtube watch history; ":ythis" keyword (requires cookies)'
    _VALID_URL = r':ythis(?:tory)?'
    _FEED_NAME = 'history'
    _TESTS = [{
        'url': ':ythistory',
        'only_matching': True,
    }]


class YoutubeShortsAudioPivotIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube Shorts audio pivot (Shorts using audio of a given video)'
    IE_NAME = 'youtube:shorts:pivot:audio'
    _VALID_URL = r'https?://(?:www\.)?youtube\.com/source/(?P<id>[\w-]{11})/shorts'
    _TESTS = [{
        'url': 'https://www.youtube.com/source/Lyj-MZSAA9o/shorts',
        'only_matching': True,
    }]

    @staticmethod
    def _generate_audio_pivot_params(video_id):
        """
        Generates sfv_audio_pivot browse params for this video id
        """
        pb_params = b'\xf2\x05+\n)\x12\'\n\x0b%b\x12\x0b%b\x1a\x0b%b' % ((video_id.encode(),) * 3)
        return urllib.parse.quote(base64.b64encode(pb_params).decode())

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            f'https://www.youtube.com/feed/sfv_audio_pivot?bp={self._generate_audio_pivot_params(video_id)}',
            ie=YoutubeTabIE)


class YoutubeConsentRedirectIE(YoutubeBaseInfoExtractor):
    IE_NAME = 'youtube:consent'
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://consent\.youtube\.com/m\?'
    _TESTS = [{
        'url': 'https://consent.youtube.com/m?continue=https%3A%2F%2Fwww.youtube.com%2Flive%2FqVv6vCqciTM%3Fcbrd%3D1&gl=NL&m=0&pc=yt&hl=en&src=1',
        'info_dict': {
            'id': 'qVv6vCqciTM',
            'ext': 'mp4',
            'age_limit': 0,
            'uploader_id': '@sana_natori',
            'comment_count': int,
            'chapters': 'count:13',
            'upload_date': '20221223',
            'thumbnail': 'https://i.ytimg.com/vi/qVv6vCqciTM/maxresdefault.jpg',
            'channel_url': 'https://www.youtube.com/channel/UCIdEIHpS0TdkqRkHL5OkLtA',
            'uploader_url': 'https://www.youtube.com/@sana_natori',
            'like_count': int,
            'release_date': '20221223',
            'tags': ['Vtuber', '月ノ美兎', '名取さな', 'にじさんじ', 'クリスマス', '3D配信'],
            'title': '【 #インターネット女クリスマス 】3Dで歌ってはしゃぐインターネットの女たち【月ノ美兎/名取さな】',
            'view_count': int,
            'playable_in_embed': True,
            'duration': 4438,
            'availability': 'public',
            'channel_follower_count': int,
            'channel_id': 'UCIdEIHpS0TdkqRkHL5OkLtA',
            'categories': ['Entertainment'],
            'live_status': 'was_live',
            'release_timestamp': 1671793345,
            'channel': 'さなちゃんねる',
            'description': 'md5:6aebf95cc4a1d731aebc01ad6cc9806d',
            'uploader': 'さなちゃんねる',
            'channel_is_verified': True,
            'heatmap': 'count:100',
        },
        'add_ie': ['Youtube'],
        'params': {'skip_download': 'Youtube'},
    }]

    def _real_extract(self, url):
        redirect_url = url_or_none(parse_qs(url).get('continue', [None])[-1])
        if not redirect_url:
            raise ExtractorError('Invalid cookie consent redirect URL', expected=True)
        return self.url_result(redirect_url)
