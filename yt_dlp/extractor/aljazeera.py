import json

from .common import InfoExtractor
from ..utils import (
    try_get,
)


class AlJazeeraIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<base>\w+\.aljazeera\.\w+)/(?P<type>programs?/[^/]+|(?:feature|video|new)s)?/\d{4}/\d{1,2}/\d{1,2}/(?P<id>[^/?&#]+)'

    _TESTS = [{
        'url': 'https://balkans.aljazeera.net/videos/2021/11/6/pojedini-domovi-u-sarajevu-jos-pod-vodom-mjestanima-se-dostavlja-hrana',
        'info_dict': {
            'id': '6280641530001',
            'ext': 'mp4',
            'title': 'Pojedini domovi u Sarajevu još pod vodom, mještanima se dostavlja hrana',
            'timestamp': 1636219149,
            'description': 'U sarajevskim naseljima Rajlovac i Reljevo stambeni objekti, ali i industrijska postrojenja i dalje su pod vodom.',
            'upload_date': '20211106',
        },
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
        base, post_type, display_id = self._match_valid_url(url).groups()
        wp = {
            'balkans.aljazeera.net': 'ajb',
            'chinese.aljazeera.net': 'chinese',
            'mubasher.aljazeera.net': 'ajm',
        }.get(base) or 'aje'
        post_type = {
            'features': 'post',
            'program': 'episode',
            'programs': 'episode',
            'videos': 'video',
            'news': 'news',
        }[post_type.split('/')[0]]
        video = self._download_json(
            f'https://{base}/graphql', display_id, query={
                'wp-site': wp,
                'operationName': 'ArchipelagoSingleArticleQuery',
                'variables': json.dumps({
                    'name': display_id,
                    'postType': post_type,
                }),
            }, headers={
                'wp-site': wp,
            })
        video = try_get(video, lambda x: x['data']['article']['video']) or {}
        video_id = video.get('id')
        account = video.get('accountId') or '911432371001'
        player_id = video.get('playerId') or 'csvTfAlKW'
        embed = 'default'

        if video_id is None:
            webpage = self._download_webpage(url, display_id)

            account, player_id, embed, video_id = self._search_regex(self.BRIGHTCOVE_URL_RE, webpage, 'video id',
                                                                     group=(1, 2, 3, 4), default=(None, None, None, None))

            if video_id is None:
                return {
                    '_type': 'url_transparent',
                    'url': url,
                    'ie_key': 'Generic',
                }

        return {
            '_type': 'url_transparent',
            'url': f'https://players.brightcove.net/{account}/{player_id}_{embed}/index.html?videoId={video_id}',
            'ie_key': 'BrightcoveNew',
        }
