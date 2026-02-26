from .mtv import MTVServicesBaseIE


class NickIE(MTVServicesBaseIE):
    IE_NAME = 'nick.com'
    _VALID_URL = r'https?://(?:www\.)?nick\.com/(?:video-clips|episodes)/(?P<id>[\da-z]{6})'
    _TESTS = [{
        'url': 'https://www.nick.com/episodes/u3smw8/wylde-pak-best-summer-ever-season-1-ep-1',
        'info_dict': {
            'id': 'eb9d4db0-274a-11ef-a913-0e37995d42c9',
            'ext': 'mp4',
            'display_id': 'u3smw8',
            'title': 'Best Summer Ever?',
            'description': 'md5:c737a0ade3fbc09d569c3b3d029a7792',
            'channel': 'Nickelodeon',
            'duration': 1296.0,
            'thumbnail': r're:https://assets\.nick\.com/uri/mgid:arc:imageassetref:',
            'series': 'Wylde Pak',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1746100800,
            'upload_date': '20250501',
            'release_timestamp': 1746100800,
            'release_date': '20250501',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nick.com/video-clips/0p4706/spongebob-squarepants-spongebob-loving-the-krusty-krab-for-7-minutes',
        'info_dict': {
            'id': '4aac2228-5295-4076-b986-159513cf4ce4',
            'ext': 'mp4',
            'display_id': '0p4706',
            'title': 'SpongeBob Loving the Krusty Krab for 7 Minutes!',
            'description': 'md5:72bf59babdf4e6d642187502864e111d',
            'duration': 423.423,
            'thumbnail': r're:https://assets\.nick\.com/uri/mgid:arc:imageassetref:',
            'series': 'SpongeBob SquarePants',
            'season': 'Season 0',
            'season_number': 0,
            'episode': 'Episode 0',
            'episode_number': 0,
            'timestamp': 1663819200,
            'upload_date': '20220922',
        },
        'params': {'skip_download': 'm3u8'},
    }]
