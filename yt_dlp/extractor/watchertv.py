from .dropout import DropoutBaseIE, DropoutSeasonBaseIE


class WatcherTVIE(DropoutBaseIE):
    _HOST = 'https://www.watchertv.com'
    _NETRC_MACHINE = 'watchertv'

    _VALID_URL = r'https?://(?:www\.)?watchertv\.com/(?:[^/]+/)*videos/(?P<id>[^/]+)/?$'
    _TESTS = [
        {
            'url': 'https://www.watchertv.com/ghost-files/season:2/videos/gf-201',
            'note': 'Episode in a series',
            'md5': '99c9aab2cb62157467b7ef5e37266e4e',
            'info_dict': {
                'id': '3129338',
                'display_id': 'gf-201',
                'ext': 'mp4',
                'title': 'The Death Row Poltergeists of Missouri State Penitentiary',
                'description': 'Where Curiosity Meets Comedy',
                'release_date': '20230825',
                'thumbnail': 'https://vhx.imgix.net/watcherentertainment/assets/92c02f39-2ed6-4b51-9e63-1a907b82e2bc.png',
                'series': 'Ghost Files',
                'season_number': 2,
                'season': 'Season 2',
                'episode_number': 1,
                'episode': 'The Death Row Poltergeists of Missouri State Penitentiary',
                'duration': 3853,
                'uploader_id': 'user80538407',
                'uploader_url': 'https://vimeo.com/user80538407',
                'uploader': 'OTT Videos',
            },
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        },
        {
            'url': 'https://www.watchertv.com/road-files/season:1/videos/rf101',
            'note': 'Episode in a series (missing release_date)',
            'md5': '02f9aaafc8ad9bd1be366cf6a61a68d8',
            'info_dict': {
                'id': '3187312',
                'display_id': 'rf101',
                'ext': 'mp4',
                'title': 'Road Files: Haunted Hill House',
                'description': 'Where Curiosity Meets Comedy',
                'thumbnail': 'https://vhx.imgix.net/watcherentertainment/assets/7445f23c-a3e7-47fb-835a-d288273e2698.png',
                'series': 'Road Files',
                'season_number': 1,
                'season': 'Season 1',
                'episode_number': 1,
                'episode': 'Road Files: Haunted Hill House',
                'duration': 516,
                'uploader_id': 'user80538407',
                'uploader_url': 'https://vimeo.com/user80538407',
                'uploader': 'OTT Videos',
            },
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        },
        {
            'url': 'https://www.watchertv.com/videos/welcome-beta-users',
            'note': 'Episode not in a series',
            'md5': 'fd1db805f9adc442c38d706bba21ad03',
            'info_dict': {
                'id': '3187107',
                'display_id': 'welcome-beta-users',
                'ext': 'mp4',
                'title': 'Welcome to Watcher!',
                'description': 'Where Curiosity Meets Comedy',
                'release_date': '20240419',
                'thumbnail': 'https://vhx.imgix.net/watcherentertainment/assets/fbb90dc8-ebb0-4597-9a83-95729e234030.jpg',
                'duration': 92,
                'uploader_id': 'user80538407',
                'uploader_url': 'https://vimeo.com/user80538407',
                'uploader': 'OTT Videos',
            },
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        },
    ]


class WatcherTVSeasonIE(DropoutSeasonBaseIE):
    _VALID_URL = r'https?://(?:www\.)?watchertv\.com/(?P<id>[^\/$&?#]+)(?:/?$|/season:(?P<season>[0-9]+)/?$)'
    _VIDEO_IE = WatcherTVIE
    _TESTS = [
        {
            'url': 'https://www.watchertv.com/ghost-files/season:1',
            'note': 'Multi-season series with the season in the url',
            'playlist_count': 8,
            'info_dict': {
                'id': 'ghost-files-season-1',
                'title': 'Ghost Files - Season 1',
            },
        },
        {
            'url': 'https://www.watchertv.com/are-you-scared',
            'note': 'Multi-season series with the season not in the url',
            'playlist_count': 3,
            'info_dict': {
                'id': 'are-you-scared-season-1',
                'title': 'Are You Scared - Season 1',
            },
        },
        {
            'url': 'https://www.watchertv.com/watcher-one-offs',
            'note': 'Single-season series',
            'playlist_count': 16,
            'info_dict': {
                'id': 'watcher-one-offs-season-1',
                'title': 'Watcher One Offs - Season 1',
            },
        },
    ]
