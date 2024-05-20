from .sheeta import SheetaEmbedIE


class NiconicoChannelPlusIE(SheetaEmbedIE):
    IE_NAME = 'NiconicoChannelPlus'
    IE_DESC = 'ニコニコチャンネルプラス'
    _VALID_URL = r'https?://nicochannel\.jp/(?P<channel>[\w.-]+)/(?:video|live)/(?P<code>sm\w+)'
    _TESTS = [{
        'url': 'https://nicochannel.jp/kaorin/video/sm89Hd4SEduy8WTsb4KxAhBL',
        'info_dict': {
            'id': 'sm89Hd4SEduy8WTsb4KxAhBL',
            'title': '前田佳織里の世界攻略計画 #2',
            'ext': 'mp4',
            'channel': '前田佳織里の世界攻略計画',
            'channel_id': 'nicochannel.jp/kaorin',
            'channel_url': 'https://nicochannel.jp/kaorin',
            'live_status': 'not_live',
            'thumbnail': str,
            'description': 'md5:02573495c8be849c0cb88df6f1b85f8b',
            'timestamp': 1644546015,
            'duration': 4093,
            'comment_count': int,
            'view_count': int,
            'tags': ['前田攻略', '前田佳織里', '前田佳織里の世界攻略計画'],
            'upload_date': '20220211',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # age limited video; test purpose channel.
        'url': 'https://nicochannel.jp/testman/video/smJPZg3nwAxP8UECPsHDiCGM',
        'info_dict': {
            'id': 'smJPZg3nwAxP8UECPsHDiCGM',
            'title': 'DW_itaba_LSM検証_1080p60fps_9000Kbpsで打ち上げたときの挙動確認（パススルーあり）',
            'ext': 'mp4',
            'channel': '本番チャンネルプラステストマン',
            'channel_id': 'nicochannel.jp/testman',
            'channel_url': 'https://nicochannel.jp/testman',
            'age_limit': 18,
            'live_status': 'was_live',
            'thumbnail': str,
            'description': 'TEST',
            'timestamp': 1701329428,
            'duration': 229,
            'comment_count': int,
            'view_count': int,
            'tags': ['検証用'],
            'upload_date': '20231130',
            'release_timestamp': 1701328800,
            'release_date': '20231130',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        return super()._extract_from_url(url)


class NiconicoChannelPlusChannelVideosIE(SheetaEmbedIE):
    IE_NAME = 'NiconicoChannelPlus:channel:videos'
    IE_DESC = 'ニコニコチャンネルプラス - チャンネル - 動画リスト. nicochannel.jp/channel/videos'
    _VALID_URL = r'https?://nicochannel\.jp/(?P<id>[a-z\d\._-]+)/videos(?:\?.*)?'
    _TESTS = [{
        # query: None
        'url': 'https://nicochannel.jp/testman/videos',
        'info_dict': {
            'id': 'nicochannel.jp/testman/videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 18,
    }, {
        # query: None
        'url': 'https://nicochannel.jp/testtarou/videos',
        'info_dict': {
            'id': 'nicochannel.jp/testtarou/videos',
            'title': 'チャンネルプラステスト太郎-videos',
        },
        'playlist_mincount': 2,
    }, {
        # query: None
        'url': 'https://nicochannel.jp/testjirou/videos',
        'info_dict': {
            'id': 'nicochannel.jp/testjirou/videos',
            'title': 'チャンネルプラステスト二郎21-videos',
        },
        'playlist_mincount': 12,
    }, {
        # query: tag
        'url': 'https://nicochannel.jp/testman/videos?tag=%E6%A4%9C%E8%A8%BC%E7%94%A8',
        'info_dict': {
            'id': 'nicochannel.jp/testman/videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 6,
    }, {
        # query: vodType
        'url': 'https://nicochannel.jp/testman/videos?vodType=1',
        'info_dict': {
            'id': 'nicochannel.jp/testman/videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 18,
    }, {
        # query: sort
        'url': 'https://nicochannel.jp/testman/videos?sort=-released_at',
        'info_dict': {
            'id': 'nicochannel.jp/testman/videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 18,
    }, {
        # query: tag, vodType
        'url': 'https://nicochannel.jp/testman/videos?tag=%E6%A4%9C%E8%A8%BC%E7%94%A8&vodType=1',
        'info_dict': {
            'id': 'nicochannel.jp/testman/videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 6,
    }, {
        # query: tag, sort
        'url': 'https://nicochannel.jp/testman/videos?tag=%E6%A4%9C%E8%A8%BC%E7%94%A8&sort=-released_at',
        'info_dict': {
            'id': 'nicochannel.jp/testman/videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 6,
    }, {
        # query: vodType, sort
        'url': 'https://nicochannel.jp/testman/videos?vodType=1&sort=-released_at',
        'info_dict': {
            'id': 'nicochannel.jp/testman/videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 18,
    }, {
        # query: tag, vodType, sort
        'url': 'https://nicochannel.jp/testman/videos?tag=%E6%A4%9C%E8%A8%BC%E7%94%A8&vodType=1&sort=-released_at',
        'info_dict': {
            'id': 'nicochannel.jp/testman/videos',
            'title': '本番チャンネルプラステストマン-videos',
        },
        'playlist_mincount': 6,
    }]

    def _real_extract(self, url):
        return super()._extract_from_url(url)


class NiconicoChannelPlusChannelLivesIE(SheetaEmbedIE):
    IE_NAME = 'NiconicoChannelPlus:channel:lives'
    IE_DESC = 'ニコニコチャンネルプラス - チャンネル - ライブリスト. nicochannel.jp/channel/lives'
    _VALID_URL = r'https?://nicochannel\.jp/(?P<id>[a-z\d\._-]+)/lives'
    _TESTS = [{
        'url': 'https://nicochannel.jp/testman/lives',
        'info_dict': {
            'id': 'nicochannel.jp/testman/lives',
            'title': '本番チャンネルプラステストマン-lives',
        },
        'playlist_mincount': 18,
    }, {
        'url': 'https://nicochannel.jp/testtarou/lives',
        'info_dict': {
            'id': 'nicochannel.jp/testtarou/lives',
            'title': 'チャンネルプラステスト太郎-lives',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://nicochannel.jp/testjirou/lives',
        'info_dict': {
            'id': 'nicochannel.jp/testjirou/lives',
            'title': 'チャンネルプラステスト二郎21-lives',
        },
        'playlist_mincount': 6,
    }]

    def _real_extract(self, url):
        return super()._extract_from_url(url)
