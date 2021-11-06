# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class AlJazeeraIE(InfoExtractor):
    _VALID_URL = r'(?x)https?://\w+\.aljazeera\.\w+/(?:programs?/[^/]+|(?:feature|video|new)s)?/\d{4}/\d{1,2}/\d{1,2}/(?P<id>[^/?&#]+)'

    _TESTS = [{
        'url': 'https://balkans.aljazeera.net/videos/2021/11/6/pojedini-domovi-u-sarajevu-jos-pod-vodom-mjestanima-se-dostavlja-hrana',
        'info_dict': {
            'id': '6280641530001',
            'ext': 'mp4',
            'title': 'Pojedini domovi u Sarajevu još pod vodom, mještanima se dostavlja hrana',
            'timestamp': 1636219149,
            'description': 'U sarajevskim naseljima Rajlovac i Reljevo stambeni objekti, ali i industrijska postrojenja i dalje su pod vodom.',
            'upload_date': '20211106',
        }
    }, {
        'url': 'https://balkans.aljazeera.net/videos/2021/11/6/djokovic-usao-u-finale-mastersa-u-parizu',
        'info_dict': {
            'id': '6280654936001',
            'ext': 'mp4',
            'title': 'Đoković ušao u finale Mastersa u Parizu',
            'timestamp': 1636221686,
            'description': 'Novak Đoković je u polufinalu Mastersa u Parizu nakon preokreta pobijedio Poljaka Huberta Hurkacza.',
            'upload_date': '20211106',
        },
    }]
    BRIGHTCOVE_URL_RE = r'https?://players.brightcove.net/(?P<account>\d+)/(?P<player_id>[a-zA-Z0-9]+)_(?P<embed>[^/]+)/index.html\?videoId=(?P<id>\d+)'

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)

        account, player_id, embed, video_id = self._search_regex(self.BRIGHTCOVE_URL_RE, webpage, 'video id',
                                                                 group=(1, 2, 3, 4), default=(None, None, None, None))
        if None in (account, player_id, embed, id):
            return {
                '_type': 'url_transparent',
                'url': url,
                'ie_key': 'Generic'
            }

        return {
            '_type': 'url_transparent',
            'url': f'https://players.brightcove.net/{account}/{player_id}_{embed}/index.html?videoId={player_id}',
            'ie_key': 'BrightcoveNew'
        }
