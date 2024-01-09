from .mtv import MTVServicesInfoExtractor


class LogoTVIE(MTVServicesInfoExtractor):
    IE_NAME = 'logotv.com'
    _FEED_URL = 'http://feeds.mtvnservices.com/od/feed/intl-mrss-player-feed'

    _TESTS = [{
        'url': 'https://www.logotv.com/episodes/6z2rdh/gay-chorus-deep-south-gay-chorus-deep-south-season-1-ep-1',
        'info_dict': {
            'title': 'Gay Chorus Deep South | HDMC6173A eng | Version: 1055407 | Logo S10',
            'description': "In response to a wave of discriminatory anti-LGBTQ laws and the divisive 2016 election, the San Francisco Gay Men's Chorus embarks on a tour of the American Deep South.",
            'duration': 504.0,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://www.logotv.com/episodes/euw2gp/fire-island-welcome-to-fire-island-season-1-ep-1',
        'info_dict': {
            'id': 'f7ee1c4b-6295-4c31-863d-9662f0ea63da',
            'title': 'Fire Island | Welcome to Fire Island | E 101 | HDQFIP101A eng | Version: 799451 | LOGO S1',
            'duration': 108.0,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    _VALID_URL = r'https?://(?:www\.)?logotv\.com/episodes/(?P<id>[^/?#.]+)'

    def _get_feed_query(self, uri):
        return {
            'arcEp': 'logotv.com',
            'mgid': uri,
        }
