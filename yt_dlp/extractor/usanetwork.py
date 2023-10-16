from .nbc import NBCIE


class USANetworkIE(NBCIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?(?P<permalink>://(?:www\.)?usanetwork\.com/(?:[^/]+/videos?|movies?)/(?:[^/]+/)?(?P<id>\d+))'
    _TESTS = [{
        'url': 'https://www.usanetwork.com/peacock-trailers/video/intelligence-trailer/4185302',
        'info_dict': {
            'id': '4185302',
            'ext': 'mp4',
            'title': 'Intelligence (Trailer)',
            'description': 'A maverick NSA agent enlists the help of a junior systems analyst in a workplace power grab.',
            'upload_date': '20200715',
            'timestamp': 1594785600,
            'uploader': 'NBCU-MPAT',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]
