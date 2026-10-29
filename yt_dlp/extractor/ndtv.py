from .common import InfoExtractor
from ..utils import (
    clean_html,
    parse_duration,
    str_or_none,
    traverse_obj,
    unescapeHTML,
    unified_timestamp,
    url_or_none,
)


class NDTVIE(InfoExtractor):
    _WORKING = True
    IE_NAME = 'ndtv:video'
    _VALID_URL = r'https?://(?:[^/]+\.)?ndtv\.com/(?:[^#/]+/)*videos?/?(?:[^#/]+/)*[^/?^&]+-(?P<id>\d+)'

    _TESTS = [
        {
            'url': 'https://khabar.ndtv.com/video/show/prime-time/prime-time-ill-system-and-poor-education-468818',
            'md5': '5237500d57c8af47a519c4af9e2fd9c0',
            'info_dict': {
                'id': '468818',
                'ext': 'mp4',
                'title': 'प्राइम टाइम: सिस्टम बीमार, स्कूल बदहाल',
                'description': 'md5:de6008f2439005344c1c0c686032b43a',
                'upload_date': '20170928',
                'timestamp': 1506612600.0,
                'duration': 2218,
                'thumbnail': r're:https?://.*\.jpg',
                'categories': ['shows'],
                'channel_id': '2',
            },
        },
        {
            'url': 'http://movies.ndtv.com/videos/cracker-free-diwali-wishes-from-karan-johar-kriti-sanon-other-stars-470304',
            'md5': 'b7ef90f55e63885aef59c59cf2e44e81',
            'info_dict': {
                'id': '470304',
                'ext': 'mp4',
                'title': 'Cracker-Free Diwali Wishes From Karan Johar, Kriti Sanon & Other Stars',
                'description': 'md5:f115bba1adf2f6433fa7c1ade5feb465',
                'upload_date': '20171018',
                'timestamp': 1508352987.0,
                'duration': 137,
                'thumbnail': r're:https?://.*\.jpg',
                'categories': ['entertainment'],
                'channel_id': '1',
            },
        },
        {
            'url': 'https://www.ndtv.com/video/ndtv-jai-jawan-dnd-john-abraham-is-busy-watching-soldiers-fitness-routine-826286',
            'md5': '443cbf0b7dd82089f5ebb11804fbc892',
            'info_dict': {
                'id': '826286',
                'ext': 'mp4',
                'title': 'NDTV Jai Jawan: DND, John Abraham Is Busy Watching Soldiers\' Fitness Routine',
                'description': 'md5:ad700713b10702555555e6a01a25442a',
                'upload_date': '20240818',
                'timestamp': 1723964765.0,
                'duration': 220,
                'thumbnail': r're:https?://.*\.jpg',
                'categories': ['entertainment'],
                'channel_id': '1',
            },
        },
        {
            'url': 'https://www.ndtv.com/video/cancer-can-be-prevented-cured-with-lifestyle-changes-expert-to-ndtv-827194',
            'md5': '3bb5e431246a5d6431affc0e26cec4a0',
            'info_dict': {
                'id': '827194',
                'ext': 'mp4',
                'title': '"Cancer Can Be Prevented, Cured With Lifestyle Changes": Expert To NDTV',
                'description': 'md5:cbecc6372e33370014748db9ad2b5df0',
                'upload_date': '20240818',
                'timestamp': 1723970085.0,
                'duration': 931,
                'thumbnail': r're:https?://.*\.jpg',
                'categories': ['news'],
                'channel_id': '1',
            },
        },
        {
            'url': 'https://sports.ndtv.com/cricket/videos/ex-india-captain-ms-dhoni-spotted-at-airport-820044',
            'md5': '57ef9cee36e0178ef1b67a879300eee1',
            'info_dict': {
                'id': '820044',
                'ext': 'mp4',
                'title': 'Ex-India Captain MS Dhoni Spotted At Airport',
                'description': 'md5:7be70dbb543bb647f83dbd6e7b8f16a0',
                'upload_date': '20240730',
                'timestamp': 1722336305.0,
                'duration': 45,
                'thumbnail': r're:https?://.*\.jpg',
                'categories': ['fangully'],
                'channel_id': '',
            },
        },
        {
            'url': 'https://doctor.ndtv.com/videos/attack-the-heart-attack-a-public-awareness-initiative-by-medtronics-822292',
            'md5': '74c9715df47630dd9abbcb64ec3c988f',
            'info_dict': {
                'id': '822292',
                'ext': 'mp4',
                'title': 'Attack The Heart Attack - A Public Awareness Initiative By Medtronics',
                'description': 'md5:31b876e23795b4d7ef91797f88b22730',
                'upload_date': '20240805',
                'timestamp': 1722816000,
                'duration': 1304,
                'thumbnail': r're:https?://.*\.jpg',
                'categories': ['Health'],
                'channel_id': '1',
            },
        },
        {
            'url': 'https://food.ndtv.com/video-watch-ndtv-food-awards-2024-on-ndtv-24x7-on-saturday-9th-march-2024-767098',
            'md5': '78ddea4f057115e84952563749c6b94c',
            'info_dict': {
                'id': '767098',
                'ext': 'mp4',
                'title': 'Watch NDTV Food Awards 2024 On NDTV 24x7 On Saturday 9th March, 2024',
                'description': 'md5:11948e8404b058cd0a9d174aa1e88e84',
                'upload_date': '20240307',
                'timestamp': 1709799526.0,
                'duration': 35,
                'thumbnail': r're:https?://.*\.jpg',
                'categories': ['food'],
                'channel_id': '1',
            },
        },
        {
            'url': 'https://www.ndtv.com/video/news/news/delhi-s-air-quality-status-report-after-diwali-is-very-poor-470372',
            'only_matching': True,
        },
        {
            'url': 'https://auto.ndtv.com/videos/the-cnb-daily-october-13-2017-469935',
            'only_matching': True,
        },
        {
            'url': 'https://sports.ndtv.com/cricket/videos/2nd-t20i-rock-thrown-at-australia-cricket-team-bus-after-win-over-india-469764',
            'only_matching': True,
        },
        {
            'url': 'http://gadgets.ndtv.com/videos/uncharted-the-lost-legacy-review-465568',
            'only_matching': True,
        },
        {
            'url': 'http://profit.ndtv.com/videos/news/video-indian-economy-on-very-solid-track-international-monetary-fund-chief-470040',
            'only_matching': True,
        },
        {
            'url': 'http://food.ndtv.com/video-basil-seeds-coconut-porridge-419083',
            'only_matching': True,
        },
        {
            'url': 'https://doctor.ndtv.com/videos/top-health-stories-of-the-week-467396',
            'only_matching': True,
        },
        {
            'url': 'https://swirlster.ndtv.com/video/how-to-make-friends-at-work-469324',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # required for removing unwanted js expression in the json data
        # found this expression in one article
        # will update this json data handler more generic if more of similar patterns found
        webpage = webpage.replace('true / false', 'true')
        json_data = self._search_json(r'__html5playerdata\s*=\s*', webpage, 'json_data', video_id)

        video_data = traverse_obj(json_data, {
            'id': ('id', {str_or_none}),
            'title': ('title', {unescapeHTML}, {clean_html}),
            'description': ('description', {unescapeHTML}, {clean_html}),
            'duration': ('dur', {parse_duration}),
            'thumbnail': ('image', {url_or_none}),
            'categories': ('category', {str}, all),
            'timestamp': ('date', {unified_timestamp}),
            'channel_id': ('channel', {str}),
        })

        formats = []
        video_m3u8 = traverse_obj(json_data, ('media', {url_or_none}))
        video_mp4 = traverse_obj(json_data, ('media_mp4', {url_or_none}))
        video_webm = traverse_obj(json_data, ('media_webm', {url_or_none}))
        if video_mp4:
            formats.append({'url': video_mp4})
        if video_webm:
            formats.append({'url': video_webm})
        if video_m3u8:
            formats.extend(self._extract_m3u8_formats(video_m3u8, video_id))
        video_data['formats'] = formats

        return video_data
