from .fox import FOXIE


class NationalGeographicTVIE(FOXIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?://(?:www\.)?nationalgeographic\.com/tv/watch/(?P<id>[\da-fA-F]+)'
    _TESTS = [{
        'url': 'https://www.nationalgeographic.com/tv/watch/6a875e6e734b479beda26438c9f21138/',
        'info_dict': {
            'id': '6a875e6e734b479beda26438c9f21138',
            'ext': 'mp4',
            'title': 'Why Nat Geo? Valley of the Boom',
            'description': 'The lives of prominent figures in the tech world, including their friendships, rivalries, victories and failures.',
            'timestamp': 1542662458,
            'upload_date': '20181119',
            'age_limit': 14,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Content not available',
    }]
    _HOME_PAGE_URL = 'https://www.nationalgeographic.com/tv/'
    _API_KEY = '238bb0a0c2aba67922c48709ce0c06fd'
