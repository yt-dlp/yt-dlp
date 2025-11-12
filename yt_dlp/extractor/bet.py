from .mtv import MTVServicesBaseIE


class BetIE(MTVServicesBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bet\.com/(?:video-clips|episodes)/(?P<id>[\da-z]{6})'
    _TESTS = [{
        'url': 'https://www.bet.com/video-clips/w9mk7v',
        'info_dict': {
            'id': '3022d121-d191-43fd-b5fb-b2c26f335497',
            'ext': 'mp4',
            'display_id': 'w9mk7v',
            'title': 'New Normal',
            'description': 'md5:d7898c124713b4646cecad9d16ff01f3',
            'duration': 30.08,
            'series': 'Tyler Perry\'s Sistas',
            'season': 'Season 0',
            'season_number': 0,
            'episode': 'Episode 0',
            'episode_number': 0,
            'timestamp': 1755269073,
            'upload_date': '20250815',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.bet.com/episodes/nmce72/tyler-perry-s-sistas-heavy-is-the-crown-season-9-ep-5',
        'info_dict': {
            'id': '6427562b-3029-11f0-b405-16fff45bc035',
            'ext': 'mp4',
            'display_id': 'nmce72',
            'title': 'Heavy Is the Crown',
            'description': 'md5:1ed345d3157a50572d2464afcc7a652a',
            'channel': 'BET',
            'duration': 2550.0,
            'thumbnail': r're:https://images\.paramount\.tech/uri/mgid:arc:imageassetref',
            'series': 'Tyler Perry\'s Sistas',
            'season': 'Season 9',
            'season_number': 9,
            'episode': 'Episode 5',
            'episode_number': 5,
            'timestamp': 1755165600,
            'upload_date': '20250814',
            'release_timestamp': 1755129600,
            'release_date': '20250814',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Requires provider sign-in',
    }]
