from __future__ import unicode_literals

from .common import InfoExtractor
from .cbs import CBSBaseIE
from ..utils import (
    int_or_none,
    url_or_none,
)


class ParamountPlusIE(CBSBaseIE):
    _VALID_URL = r'''(?x)
        (?:
            paramountplus:|
            https?://(?:www\.)?(?:
                paramountplus\.com/(?:shows/[^/]+/video|movies/[^/]+)/
        )(?P<id>[\w-]+))'''

    # All tests are blocked outside US
    _TESTS = [{
        'url': 'https://www.paramountplus.com/shows/catdog/video/Oe44g5_NrlgiZE3aQVONleD6vXc8kP0k/catdog-climb-every-catdog-the-canine-mutiny/',
        'info_dict': {
            'id': 'Oe44g5_NrlgiZE3aQVONleD6vXc8kP0k',
            'ext': 'mp4',
            'title': 'CatDog - Climb Every CatDog/The Canine Mutiny',
            'description': 'md5:7ac835000645a69933df226940e3c859',
            'duration': 1418,
            'timestamp': 920264400,
            'upload_date': '19990301',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.paramountplus.com/shows/tooning-out-the-news/video/6hSWYWRrR9EUTz7IEe5fJKBhYvSUfexd/7-23-21-week-in-review-rep-jahana-hayes-howard-fineman-sen-michael-bennet-sheera-frenkel-cecilia-kang-/',
        'info_dict': {
            'id': '6hSWYWRrR9EUTz7IEe5fJKBhYvSUfexd',
            'ext': 'mp4',
            'title': '7/23/21 WEEK IN REVIEW (Rep. Jahana Hayes/Howard Fineman/Sen. Michael Bennet/Sheera Frenkel & Cecilia Kang)',
            'description': 'md5:f4adcea3e8b106192022e121f1565bae',
            'duration': 2506,
            'timestamp': 1627063200,
            'upload_date': '20210723',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.paramountplus.com/movies/daddys-home/vM2vm0kE6vsS2U41VhMRKTOVHyQAr6pC',
        'info_dict': {
            'id': 'vM2vm0kE6vsS2U41VhMRKTOVHyQAr6pC',
            'ext': 'mp4',
            'title': 'Daddy\'s Home',
            'upload_date': '20151225',
            'description': 'md5:a0beaf24e8d3b0e81b2ee41d47c06f33',
            'uploader': 'CBSI-NEW',
            'timestamp': 1451030400,
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'expected_warnings': ['Ignoring subtitle tracks'],  # TODO: Investigate this
    }, {
        'url': 'https://www.paramountplus.com/movies/sonic-the-hedgehog/5EKDXPOzdVf9voUqW6oRuocyAEeJGbEc',
        'info_dict': {
            'id': '5EKDXPOzdVf9voUqW6oRuocyAEeJGbEc',
            'ext': 'mp4',
            'uploader': 'CBSI-NEW',
            'description': 'md5:bc7b6fea84ba631ef77a9bda9f2ff911',
            'timestamp': 1577865600,
            'title': 'Sonic the Hedgehog',
            'upload_date': '20200101',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'expected_warnings': ['Ignoring subtitle tracks'],
    }, {
        'url': 'https://www.paramountplus.com/shows/all-rise/video/QmR1WhNkh1a_IrdHZrbcRklm176X_rVc/all-rise-space/',
        'only_matching': True,
    }, {
        'url': 'https://www.paramountplus.com/movies/million-dollar-american-princesses-meghan-and-harry/C0LpgNwXYeB8txxycdWdR9TjxpJOsdCq',
        'only_matching': True,
    }]

    def _extract_video_info(self, content_id, mpx_acc=2198311517):
        items_data = self._download_json(
            'https://www.paramountplus.com/apps-api/v2.0/androidtv/video/cid/%s.json' % content_id,
            content_id, query={'locale': 'en-us', 'at': 'ABCqWNNSwhIqINWIIAG+DFzcFUvF8/vcN6cNyXFFfNzWAIvXuoVgX+fK4naOC7V8MLI='}, headers=self.geo_verification_headers())

        asset_types = {
            item.get('assetType'): {
                'format': 'SMIL',
                'formats': 'MPEG4,M3U',
            } for item in items_data['itemList']
        }
        item = items_data['itemList'][-1]
        return self._extract_common_video_info(content_id, asset_types, mpx_acc, extra_info={
            'title': item.get('title'),
            'series': item.get('seriesTitle'),
            'season_number': int_or_none(item.get('seasonNum')),
            'episode_number': int_or_none(item.get('episodeNum')),
            'duration': int_or_none(item.get('duration')),
            'thumbnail': url_or_none(item.get('thumbnail')),
        })


class ParamountPlusSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?paramountplus\.com/shows/(?P<id>[a-zA-Z0-9-_]+)/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://www.paramountplus.com/shows/drake-josh',
        'playlist_mincount': 50,
        'info_dict': {
            'id': 'drake-josh',
        }
    }, {
        'url': 'https://www.paramountplus.com/shows/hawaii_five_0/',
        'playlist_mincount': 240,
        'info_dict': {
            'id': 'hawaii_five_0',
        }
    }, {
        'url': 'https://www.paramountplus.com/shows/spongebob-squarepants/',
        'playlist_mincount': 248,
        'info_dict': {
            'id': 'spongebob-squarepants',
        }
    }]
    _API_URL = 'https://www.paramountplus.com/shows/{}/xhr/episodes/page/0/size/100000/xs/0/season/0/'

    def _entries(self, show_name):
        show_json = self._download_json(self._API_URL.format(show_name), video_id=show_name)
        if show_json.get('success'):
            for episode in show_json['result']['data']:
                yield self.url_result(
                    'https://www.paramountplus.com%s' % episode['url'],
                    ie=ParamountPlusIE.ie_key(), video_id=episode['content_id'])

    def _real_extract(self, url):
        show_name = self._match_id(url)
        return self.playlist_result(self._entries(show_name), playlist_id=show_name)
