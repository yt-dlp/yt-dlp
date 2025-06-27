from .mtv import MTVServicesInfoExtractor

# TODO: Remove - Reason: Outdated Site


class VH1IE(MTVServicesInfoExtractor):
    IE_NAME = 'vh1.com'
    _FEED_URL = 'http://www.vh1.com/feeds/mrss/'
    _TESTS = [{
        'url': 'https://www.vh1.com/episodes/0aqivv/nick-cannon-presents-wild-n-out-foushee-season-16-ep-12',
        'info_dict': {
            'title': 'Fousheé',
            'description': 'Fousheé joins Team Evolutions fight against Nick and Team Revolution in Baby Daddy, Baby Mama; Kick Em Out the Classroom; Backseat of My Ride and Wildstyle; and Fousheé performs.',
        },
        'playlist_mincount': 4,
        'skip': '404 Not found',
    }, {
        # Clip
        'url': 'https://www.vh1.com/video-clips/e0sja0/nick-cannon-presents-wild-n-out-foushee-clap-for-him',
        'info_dict': {
            'id': 'a07563f7-a37b-4e7f-af68-85855c2c7cc3',
            'ext': 'mp4',
            'title': 'Fousheé - "clap for him"',
            'description': 'Singer Fousheé hits the Wild N Out: In the Dark stage with a performance of the tongue-in-cheek track "clap for him" from her 2021 album "time machine."',
            'upload_date': '20210826',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    _VALID_URL = r'https?://(?:www\.)?vh1\.com/(?:video-clips|episodes)/(?P<id>[^/?#.]+)'
