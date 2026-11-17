from .mtv import MTVServicesBaseIE


class ComedyCentralIE(MTVServicesBaseIE):
    _VALID_URL = r'https?://(?:www\.)?cc\.com/video-clips/(?P<id>[\da-z]{6})'
    _TESTS = [{
        'url': 'https://www.cc.com/video-clips/wl12cx',
        'info_dict': {
            'id': 'dec6953e-80c8-43b3-96cd-05e9230e704d',
            'ext': 'mp4',
            'display_id': 'wl12cx',
            'title': 'Alison Brie and Dave Franco -"Together"- Extended Interview',
            'description': 'md5:ec68e38d3282f863de9cde0ce5cd231c',
            'duration': 516.76,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref:',
            'series': 'The Daily Show',
            'season': 'Season 30',
            'season_number': 30,
            'episode': 'Episode 0',
            'episode_number': 0,
            'timestamp': 1753973314,
            'upload_date': '20250731',
            'release_timestamp': 1753977914,
            'release_date': '20250731',
        },
        'params': {'skip_download': 'm3u8'},
    }]
