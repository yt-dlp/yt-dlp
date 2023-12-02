from .common import InfoExtractor, ExtractorError, url_or_none
from ..utils import (
    parse_iso8601,
    traverse_obj,
)


class TrtWorldIE(InfoExtractor):
    _VALID_URL = r'https?://www\.trtworld\.com/video/[\w-]+/[\w-]+-(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.trtworld.com/video/news/turkiye-switches-to-sustainable-tourism-16067690',
        'info_dict': {
            'id': '16067690',
            'ext': 'mp4',
            'title': 'Türkiye switches to sustainable tourism',
            'release_timestamp': 1701529569,
            'release_date': '20231202',
            'thumbnail': 'https://cdn-i.pr.trt.com.tr/trtworld/17647563_0-0-1920-1080.jpeg',
            'description': "Tourism sustainability is one of the main issues at COP28, as the UN calls for new ways to lessen the effects of tourism on the environment. And as a leading country in the sector, T\u00fcrkiye is doing its part with a new strategy. Asli Atbas reports from one of the country's favourite holiday destinations, Cappadocia."
        }
    }, {
        'url': 'https://www.trtworld.com/video/one-offs/frames-from-anatolia-recreating-a-james-bond-scene-in-istanbuls-grand-bazaar-14541780',
        'info_dict': {
            'id': '14541780',
            'ext': 'mp4',
            'title': 'Frames From Anatolia: Recreating a ‘James Bond’ Scene in Istanbul’s Grand Bazaar',
            'release_timestamp': 1692440844,
            'release_date': '20230819',
            'thumbnail': 'https://cdn-i.pr.trt.com.tr/trtworld/16939810_0-0-1920-1080.jpeg',
            'description': "Join us on a fun adventure as we attempt to recreate an iconic “James Bond” scene, weaving together film history and the bustling life and culture of the real world in the heart of Istanbul’s colourful Grand Bazaar!"
        }
    }, {
        'url': 'https://www.trtworld.com/video/the-newsmakers/can-sudan-find-peace-amidst-failed-transition-to-democracy-12904760',
        'info_dict': {
            'id': '12904760',
            'ext': 'mp4',
            'title': 'Can Sudan find peace amidst failed transition to democracy?',
            'release_timestamp': 1681972747,
            'release_date': '20230420',
            'thumbnail': 'http://cdni0.trtworld.com/w768/q70/154214_NMYOUTUBETEMPLATE1_1681833018736.jpg'
        }
    }, {
        'url': 'https://www.trtworld.com/video/africa-matters/locals-learning-to-cope-with-rising-tides-of-kenyas-great-lakes-16059545',
        'info_dict': {
            'id': 'zEns2dWl00w',
            'ext': 'mp4',
            'title': "Locals learning to cope with rising tides of Kenya's Great Lakes",
            "thumbnail": "https://i.ytimg.com/vi/zEns2dWl00w/maxresdefault.jpg",
            "description": "The great lakes of Kenya are a major tourist attraction, and support the livelihoods of millions of residents. But in recent years, their levels have been steadily rising, wreaking havoc. \n\nAlexandria Majalla spoke to locals to find out how they're coping with the changing tides.\r\n\r\nSubscribe:\nhttp://trt.world/subscribe\nLivestream: http://trt.world/ytlive\nFacebook: http://trt.world/facebook\nTwitter: http://trt.world/twitter\nInstagram: http://trt.world/instagram\nVisit our website: http://trt.world",
            "channel_id": "UC7fWeaHhqgM4Ry-RMpM2YYw",
            "channel_url": "https://www.youtube.com/channel/UC7fWeaHhqgM4Ry-RMpM2YYw",
            "duration": 210,
            "view_count": int,
            "average_rating": None,
            "age_limit": int,
            "webpage_url": "https://www.youtube.com/watch?v=zEns2dWl00w",
            "categories": [
                "News & Politics"
            ],
            "channel": "TRT World",
            "channel_follower_count": int,
            "channel_is_verified": bool,
            "uploader": "TRT World",
            "uploader_id": "@trtworld",
            "uploader_url": "https://www.youtube.com/@trtworld",
            "upload_date": "20231202",
            "availability": "public",
            'comment_count': int,
            'playable_in_embed': bool,
            'tags': [],
            'live_status': 'not_live',
            'like_count': None

        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        nuxtjs_data = self._search_nuxt_data(webpage, display_id)['videoData']['content']
        formats = []
        for media_url in traverse_obj(nuxtjs_data, (
                'platforms', ('website', 'ott'), 'metadata', ('hls_url', 'url'), {url_or_none})):
            # Website sometimes serves mp4 files under `hls_url` key
            if media_url.endswith('.m3u8'):
                formats.extend(self._extract_m3u8_formats(media_url, display_id, fatal=False))
            else:
                formats.append({
                    'format_id': 'http',
                    'url': media_url,
                })
        if not formats:
            if youtube_id := traverse_obj(nuxtjs_data, ('platforms', 'youtube', 'metadata', 'youtubeId')):
                return self.url_result(youtube_id, 'Youtube')
            raise ExtractorError('No video found', expected=True)

        return {
            'id': display_id,
            'formats': formats,
            **traverse_obj(nuxtjs_data, ('platforms', ('website', 'ott'), {
                'title': ('fields', 'title', 'text'),
                'description': ('fields', 'description', 'text'),
                'thumbnail': ('fields', 'thumbnail', 'url', {url_or_none}),
                'release_timestamp': ('published', 'date', {parse_iso8601}),
            }), get_all=False),
        }
