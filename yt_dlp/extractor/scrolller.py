from .common import InfoExtractor
from ..utils import (str_or_none, traverse_obj)
import json


class ScrolllerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?scrolller\.com/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://scrolller.com/a-helping-hand-1k9pxikxkw',
        'info_dict': {
            'id': '7989759',
            'ext': 'mp4',
            'title': 'A helping hand',
            "thumbnail": "https://zepto.scrolller.com/a-helping-hand-3ty9q8x094-540x960.jpg",
            "subredditTitle": "Raccoons",
            "subredditUrl": "/r/Raccoons",
            "redditPath": "/r/Raccoons/comments/90u93j/a_helping_hand/",
            "age_limit": 0,
        }
    }, {
        'url': 'https://scrolller.com/how-do-i-look-now-9sy8ply9ri',
        'info_dict': {
            "id": "4426559",
            'ext': 'jpg',
            "title": "How do I look now?",
            "thumbnail": "https://atto.scrolller.com/how-do-i-look-now-8qbj974956-540x405.jpg",
            "subredditTitle": "Maltese",
            "subredditUrl": "/r/Maltese",
            "redditPath": "/r/Maltese/comments/cddwon/how_do_i_look_now/",
            "age_limit": 0,
        }
    }, {
        'url': 'https://scrolller.com/tigers-chasing-a-drone-c5d1f2so6j',
        'info_dict': {
            "id": "3655028",
            'ext': 'mp4',
            "title": "Tigers chasing a drone",
            "thumbnail": "https://zepto.scrolller.com/tigers-chasing-a-drone-az9pkpguwe-540x303.jpg",
            "subredditTitle": "BigCatGifs",
            "subredditUrl": "/r/BigCatGifs",
            "redditPath": "/r/BigCatGifs/comments/73yuy6/tigers_chasing_a_drone/",
            "age_limit": 0,
        }
    }, {
        'url': 'https://scrolller.com/baby-rhino-smells-something-9chhugsv9p',
        'info_dict': {
            "id": "7964447",
            'ext': 'mp4',
            "title": "Baby rhino smells something",
            "thumbnail": "https://atto.scrolller.com/hmm-whats-that-smell-bh54mf2c52-300x224.jpg",
            "subredditTitle": "babyrhinogifs",
            "subredditUrl": "/r/babyrhinogifs",
            "redditPath": "/r/babyrhinogifs/comments/28n8m5/baby_rhino_smells_something/",
            "age_limit": 0,
        }
    }, {
        'url': 'https://scrolller.com/its-all-fun-and-games-cco8jjmoh7',
        'info_dict': {
            "id": "7793294",
            'ext': 'mp4',
            "title": "It\'s all fun and games...",
            "thumbnail": "https://atto.scrolller.com/its-all-fun-and-games-3amk9vg7m3-540x649.jpg",
            "subredditTitle": "CatsISUOTTATFO",
            "subredditUrl": "/r/CatsISUOTTATFO",
            "redditPath": "/r/CatsISUOTTATFO/comments/aspuho/its_all_fun_and_games/",
            "age_limit": 0,
        }
    }, {
        'url': 'https://scrolller.com/sonata-by-mario-joseph-korbel-at-brookgreen-bsosnl30q2',
        'info_dict': {
            "id": "5744948",
            'ext': 'jpg',
            "title": "\"Sonata\" by Mario Joseph Korbel at Brookgreen Gardens, SC",
            "thumbnail": "https://atto.scrolller.com/sonata-by-mario-joseph-korbel-at-brookgreen-8ydxix8voq-540x386.jpg",
            "subredditTitle": "SculpturePorn",
            "subredditUrl": "/r/SculpturePorn",
            "redditPath": "/r/SculpturePorn/comments/90frau/sonata_by_mario_joseph_korbel_at_brookgreen/",
            "age_limit": 0,
        }
    }, {
        'url': 'https://scrolller.com/halloween-is-one-of-the-best-holidays-7vu9jd4bo3',
        'info_dict': {
            "id": "6969529",
            'ext': 'jpg',
            "title": "Halloween is one of the best holidays",
            "thumbnail": "https://yocto.scrolller.com/and-this-is-why-i-love-halloween-5bqylkkzk0-640x854.jpg",
            "subredditTitle": "nsfw",
            "subredditUrl": "/r/nsfw",
            "redditPath": "/r/nsfw/comments/j84wnr/halloween_is_one_of_the_best_holidays/",
            "age_limit": 18,
        }
    },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json("https://api.scrolller.com/api/v2/graphql", video_id, data=json.dumps({
            'query': '''{
                getSubredditPost(url:"/%s"){
                    id
                    title
                    subredditTitle
                    subredditUrl
                    redditPath
                    isNsfw
                    mediaSources{
                        url
                        width
                        height
                    }
                }
            }''' % (video_id)
        }).encode(), headers={
            'Content-Type': 'application/json',
        })['data']['getSubredditPost']

        video.update({
            "id": str_or_none(video.get("id")),
            "thumbnail": traverse_obj(video, "mediaSources")[0].get("url"),
            "formats": traverse_obj(video, "mediaSources"),
            "age_limit": 18 if video.get("isNsfw") else 0
        })

        del video['isNsfw']
        del video['mediaSources']

        return video
