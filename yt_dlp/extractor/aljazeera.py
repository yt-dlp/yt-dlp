from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor


class AlJazeeraIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?aljazeera\.com/(?P<type>program/[^/]+|(?:feature|video)s)/\d{4}/\d{1,2}/\d{1,2}/(?P<id>[^/?&#]+)'

    _TESTS = [{
        'url': 'https://www.aljazeera.com/program/episode/2014/9/19/deliverance',
        'info_dict': {
            'id': '3792260579001',
            'ext': 'mp4',
            'title': 'The Slum - Episode 1: Deliverance',
            'description': 'As a birth attendant advocating for family planning, Remy is on the frontline of Tondo\'s battle with overcrowding.',
            'uploader_id': '665003303001',
            'timestamp': 1411116829,
            'upload_date': '20140919',
        },
        'add_ie': ['BrightcoveNew'],
        'skip': 'Not accessible from Travis CI server',
    }, {
        'url': 'https://www.aljazeera.com/videos/2017/5/11/sierra-leone-709-carat-diamond-to-be-auctioned-off',
        'only_matching': True,
    }, {
        'url': 'https://www.aljazeera.com/features/2017/8/21/transforming-pakistans-buses-into-art',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'

    def _real_extract(self, url):
        post_type, name = re.match(self._VALID_URL, url).groups()
        post_type = {
            'features': 'post',
            'program': 'episode',
            'videos': 'video',
        }[post_type.split('/')[0]]
        video = self._download_json(
            'https://www.aljazeera.com/graphql', name, query={
                'operationName': 'SingleArticleQuery',
                'variables': json.dumps({
                    'name': name,
                    'postType': post_type,
                }),
            }, headers={
                'wp-site': 'aje',
            })['data']['article']['video']
        video_id = video['id']
        account_id = video.get('accountId') or '665003303001'
        player_id = video.get('playerId') or 'BkeSH5BDb'
        return self.url_result(
            self.BRIGHTCOVE_URL_TEMPLATE % (account_id, player_id, video_id),
            'BrightcoveNew', video_id)
