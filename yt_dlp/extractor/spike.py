from __future__ import unicode_literals

from .mtv import MTVServicesInfoExtractor


class BellatorIE(MTVServicesInfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bellator\.com/[^/]+/[\da-z]{6}(?:[/?#&]|$)'
    _TESTS = [{
        'url': 'http://www.bellator.com/fight/atwr7k/bellator-158-michael-page-vs-evangelista-cyborg',
        'info_dict': {
            'title': 'Michael Page vs. Evangelista Cyborg',
            'description': 'md5:0d917fc00ffd72dd92814963fc6cbb05',
        },
        'playlist_count': 3,
    }, {
        'url': 'http://www.bellator.com/video-clips/bw6k7n/bellator-158-foundations-michael-venom-page',
        'only_matching': True,
    }]

    _FEED_URL = 'http://www.bellator.com/feeds/mrss/'
    _GEO_COUNTRIES = ['US']


class ParamountNetworkIE(MTVServicesInfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?paramountnetwork\.com/[^/]+/[\da-z]{6}(?:[/?#&]|$)'
    _TESTS = [{
        'url': 'http://www.paramountnetwork.com/episodes/j830qm/lip-sync-battle-joel-mchale-vs-jim-rash-season-2-ep-13',
        'info_dict': {
            'id': '37ace3a8-1df6-48be-85b8-38df8229e241',
            'ext': 'mp4',
            'title': 'Lip Sync Battle|April 28, 2016|2|209|Joel McHale Vs. Jim Rash|Act 1',
            'description': 'md5:a739ca8f978a7802f67f8016d27ce114',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    _FEED_URL = 'http://feeds.mtvnservices.com/od/feed/intl-mrss-player-feed'
    _GEO_COUNTRIES = ['US']

    def _get_feed_query(self, uri):
        return {
            'arcEp': 'paramountnetwork.com',
            'imageEp': 'paramountnetwork.com',
            'mgid': uri,
        }
