from .mtv import MTVServicesBaseIE


class VH1IE(MTVServicesBaseIE):
    IE_NAME = 'vh1.com'
    _VALID_URL = r'https?://(?:www\.)?vh1\.com/(?:video-clips|episodes)/(?P<id>[\da-z]{6})'
    _TESTS = [{
        'url': 'https://www.vh1.com/episodes/d06ta1/barely-famous-barely-famous-season-1-ep-1',
        'info_dict': {
            'id': '4af4cf2c-a854-11e4-9596-0026b9414f30',
            'ext': 'mp4',
            'display_id': 'd06ta1',
            'title': 'Barely Famous',
            'description': 'md5:6da5c9d88012eba0a80fc731c99b5fed',
            'channel': 'VH1',
            'duration': 1280.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'Barely Famous',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1426680000,
            'upload_date': '20150318',
            'release_timestamp': 1426680000,
            'release_date': '20150318',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.vh1.com/video-clips/ryzt2n/love-hip-hop-miami-love-hip-hop-miami-season-5-recap',
        'info_dict': {
            'id': '59e62974-4a5c-4417-91c3-5044cb2f4ce2',
            'ext': 'mp4',
            'display_id': 'ryzt2n',
            'title': 'Love & Hip Hop Miami - Season 5 Recap',
            'description': 'md5:4e49c65d0007bfc8d06db555a6b76ef0',
            'duration': 792.083,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'Love & Hip Hop Miami',
            'season': 'Season 6',
            'season_number': 6,
            'episode': 'Episode 0',
            'episode_number': 0,
            'timestamp': 1732597200,
            'upload_date': '20241126',
            'release_timestamp': 1732597200,
            'release_date': '20241126',
        },
        'params': {'skip_download': 'm3u8'},
    }]
