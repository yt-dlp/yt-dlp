import json

from .common import InfoExtractor
from ..utils import determine_ext, int_or_none


class ScrolllerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?scrolller\.com/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://scrolller.com/a-helping-hand-1k9pxikxkw',
        'info_dict': {
            'id': 'a-helping-hand-1k9pxikxkw',
            'ext': 'mp4',
            'thumbnail': 'https://zepto.scrolller.com/a-helping-hand-3ty9q8x094-540x960.jpg',
            'title': 'A helping hand',
            'age_limit': 0,
        }
    }, {
        'url': 'https://scrolller.com/tigers-chasing-a-drone-c5d1f2so6j',
        'info_dict': {
            'id': 'tigers-chasing-a-drone-c5d1f2so6j',
            'ext': 'mp4',
            'thumbnail': 'https://zepto.scrolller.com/tigers-chasing-a-drone-az9pkpguwe-540x303.jpg',
            'title': 'Tigers chasing a drone',
            'age_limit': 0,
        }
    }, {
        'url': 'https://scrolller.com/baby-rhino-smells-something-9chhugsv9p',
        'info_dict': {
            'id': 'baby-rhino-smells-something-9chhugsv9p',
            'ext': 'mp4',
            'thumbnail': 'https://atto.scrolller.com/hmm-whats-that-smell-bh54mf2c52-300x224.jpg',
            'title': 'Baby rhino smells something',
            'age_limit': 0,
        }
    }, {
        'url': 'https://scrolller.com/its-all-fun-and-games-cco8jjmoh7',
        'info_dict': {
            'id': 'its-all-fun-and-games-cco8jjmoh7',
            'ext': 'mp4',
            'thumbnail': 'https://atto.scrolller.com/its-all-fun-and-games-3amk9vg7m3-540x649.jpg',
            'title': 'It\'s all fun and games...',
            'age_limit': 0,
        }
    }, {
        'url': 'https://scrolller.com/may-the-force-be-with-you-octokuro-yeytg1fs7a',
        'info_dict': {
            'id': 'may-the-force-be-with-you-octokuro-yeytg1fs7a',
            'ext': 'mp4',
            'thumbnail': 'https://thumbs2.redgifs.com/DarkStarchyNautilus-poster.jpg',
            'title': 'May the force be with you (Octokuro)',
            'age_limit': 18,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        query = {
            'query': '''{
                getSubredditPost(url:"/%s"){
                    id
                    title
                    isNsfw
                    mediaSources{
                        url
                        width
                        height
                    }
                }
            }''' % video_id
        }

        video_data = self._download_json(
            'https://api.scrolller.com/api/v2/graphql', video_id, data=json.dumps(query).encode(),
            headers={'Content-Type': 'application/json'})['data']['getSubredditPost']

        formats, thumbnails = [], []
        for source in video_data['mediaSources']:
            if determine_ext(source.get('url')) in ('jpg', 'png'):
                thumbnails.append({
                    'url': source['url'],
                    'width': int_or_none(source.get('width')),
                    'height': int_or_none(source.get('height')),
                })
            elif source.get('url'):
                formats.append({
                    'url': source['url'],
                    'width': int_or_none(source.get('width')),
                    'height': int_or_none(source.get('height')),
                })

        if not formats:
            self.raise_no_formats('There is no video.', expected=True, video_id=video_id)

        return {
            'id': video_id,
            'title': video_data.get('title'),
            'thumbnails': thumbnails,
            'formats': formats,
            'age_limit': 18 if video_data.get('isNsfw') else 0
        }
