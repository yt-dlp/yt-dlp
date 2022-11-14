from .mtv import MTVServicesInfoExtractor

# TODO: Remove - Reason not used anymore - Service moved to youtube


class TVLandIE(MTVServicesInfoExtractor):
    IE_NAME = 'tvland.com'
    _VALID_URL = r'https?://(?:www\.)?tvland\.com/(?:video-clips|(?:full-)?episodes)/(?P<id>[^/?#.]+)'
    _FEED_URL = 'http://www.tvland.com/feeds/mrss/'
    _TESTS = [{
        # Geo-restricted. Without a proxy metadata are still there. With a
        # proxy it redirects to http://m.tvland.com/app/
        'url': 'https://www.tvland.com/episodes/s04pzf/everybody-loves-raymond-the-dog-season-1-ep-19',
        'info_dict': {
            'description': 'md5:84928e7a8ad6649371fbf5da5e1ad75a',
            'title': 'The Dog',
        },
        'playlist_mincount': 5,
        'skip': '404 Not found',
    }, {
        'url': 'https://www.tvland.com/video-clips/4n87f2/younger-a-first-look-at-younger-season-6',
        'md5': 'e2c6389401cf485df26c79c247b08713',
        'info_dict': {
            'id': '891f7d3c-5b5b-4753-b879-b7ba1a601757',
            'ext': 'mp4',
            'title': 'Younger|April 30, 2019|6|NO-EPISODE#|A First Look at Younger Season 6',
            'description': 'md5:595ea74578d3a888ae878dfd1c7d4ab2',
            'upload_date': '20190430',
            'timestamp': 1556658000,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.tvland.com/full-episodes/iu0hz6/younger-a-kiss-is-just-a-kiss-season-3-ep-301',
        'only_matching': True,
    }]
