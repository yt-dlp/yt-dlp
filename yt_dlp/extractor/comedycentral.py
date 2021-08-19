from __future__ import unicode_literals

from .mtv import MTVServicesInfoExtractor


class ComedyCentralIE(MTVServicesInfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cc\.com/(?:episodes|video(?:-clips)?)/(?P<id>[0-9a-z]{6})'
    _FEED_URL = 'http://comedycentral.com/feeds/mrss/'

    _TESTS = [{
        'url': 'http://www.cc.com/video-clips/5ke9v2/the-daily-show-with-trevor-noah-doc-rivers-and-steve-ballmer---the-nba-player-strike',
        'md5': 'b8acb347177c680ff18a292aa2166f80',
        'info_dict': {
            'id': '89ccc86e-1b02-4f83-b0c9-1d9592ecd025',
            'ext': 'mp4',
            'title': 'The Daily Show with Trevor Noah|August 28, 2020|25|25149|Doc Rivers and Steve Ballmer - The NBA Player Strike',
            'description': 'md5:5334307c433892b85f4f5e5ac9ef7498',
            'timestamp': 1598670000,
            'upload_date': '20200829',
        },
    }, {
        'url': 'http://www.cc.com/episodes/pnzzci/drawn-together--american-idol--parody-clip-show-season-3-ep-314',
        'only_matching': True,
    }, {
        'url': 'https://www.cc.com/video/k3sdvm/the-daily-show-with-jon-stewart-exclusive-the-fourth-estate',
        'only_matching': True,
    }]


class ComedyCentralTVIE(MTVServicesInfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?comedycentral\.tv/folgen/(?P<id>[0-9a-z]{6})'
    _TESTS = [{
        'url': 'https://www.comedycentral.tv/folgen/pxdpec/josh-investigates-klimawandel-staffel-1-ep-1',
        'info_dict': {
            'id': '15907dc3-ec3c-11e8-a442-0e40cf2fc285',
            'ext': 'mp4',
            'title': 'Josh Investigates',
            'description': 'Steht uns das Ende der Welt bevor?',
        },
    }]
    _FEED_URL = 'http://feeds.mtvnservices.com/od/feed/intl-mrss-player-feed'
    _GEO_COUNTRIES = ['DE']

    def _get_feed_query(self, uri):
        return {
            'accountOverride': 'intl.mtvi.com',
            'arcEp': 'web.cc.tv',
            'ep': 'b9032c3a',
            'imageEp': 'web.cc.tv',
            'mgid': uri,
        }
