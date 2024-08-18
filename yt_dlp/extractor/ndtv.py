
from .common import InfoExtractor
from ..utils import clean_html, parse_duration, remove_end, unified_strdate


class NDTVIE(InfoExtractor):
    _WORKING = True
    _VALID_URL = r'https?://(?:[^/]+\.)?ndtv\.com/(?:[^/]+/)*videos?/?(?:[^/]+/)*[^/?^&]+-(?P<id>\d+)'

    _TESTS = [
        {
            'url': 'https://khabar.ndtv.com/video/show/prime-time/prime-time-ill-system-and-poor-education-468818',
            'md5': '78efcf3880ef3fd9b83d405ca94a38eb',
            'info_dict': {
                'id': '468818',
                'ext': 'mp4',
                'title': 'प्राइम टाइम: सिस्टम बीमार, स्कूल बदहाल',
                'description': 'md5:de6008f2439005344c1c0c686032b43a',
                'upload_date': '20170928',
                'duration': 2218,
                'thumbnail': r're:https?://.*\.jpg',
            },
        },
        {
            'url': 'http://movies.ndtv.com/videos/cracker-free-diwali-wishes-from-karan-johar-kriti-sanon-other-stars-470304',
            'md5': 'f1d709352305b44443515ac56b45aa46',
            'info_dict': {
                'id': '470304',
                'ext': 'mp4',
                'title': 'Cracker-Free Diwali Wishes From Karan Johar, Kriti Sanon & Other Stars',
                'description': 'md5:f115bba1adf2f6433fa7c1ade5feb465',
                'upload_date': '20171019',
                'duration': 137,
                'thumbnail': r're:https?://.*\.jpg',
            },
        },
        {
            'url': 'https://www.ndtv.com/video/ndtv-jai-jawan-dnd-john-abraham-is-busy-watching-soldiers-fitness-routine-826286',
            'md5': '19d9a96480a8dac0e03a42efce27350f',
            'info_dict': {
                'id': '826286',
                'ext': 'mp4',
                'title': 'NDTV Jai Jawan: DND, John Abraham Is Busy Watching Soldiers\' Fitness Routine',
                'description': 'md5:ad700713b10702555555e6a01a25442a',
                'upload_date': '20240818',
                'duration': 220,
                'thumbnail': 'https://c.ndtvimg.com/2024-08/be8djnjc_jai-jawan_640x480_18_August_24.jpg',
            },
        },
        {
            'url': 'https://www.ndtv.com/video/cancer-can-be-prevented-cured-with-lifestyle-changes-expert-to-ndtv-827194',
            'md5': '72734ed9226e200454100ffe7dfae2b6',
            'info_dict': {
                'id': '827194',
                'ext': 'mp4',
                'title': '"Cancer Can Be Prevented, Cured With Lifestyle Changes": Expert To NDTV',
                'description': 'md5:cbecc6372e33370014748db9ad2b5df0',
                'upload_date': '20240818',
                'duration': 931,
                'thumbnail': 'https://c.ndtvimg.com/2024-08/hh48aduk_dr-sameer-kaul_640x480_18_August_24.jpg',
            },
        },
        {
            'url': 'https://sports.ndtv.com/cricket/videos/ex-india-captain-ms-dhoni-spotted-at-airport-820044',
            'md5': '9f3442f49aa660623e8925c0fc7606a4',
            'info_dict': {
                'id': '820044',
                'ext': 'mp4',
                'title': 'Ex-India Captain MS Dhoni Spotted At Airport',
                'description': 'md5:7be70dbb543bb647f83dbd6e7b8f16a0',
                'upload_date': '20240730',
                'duration': 45,
                'thumbnail': 'https://c.ndtvimg.com/2024-07/itrg8ilo_msdhoni_640x480_31_July_24.jpg',
            },
        },
        {
            'url': 'https://doctor.ndtv.com/videos/attack-the-heart-attack-a-public-awareness-initiative-by-medtronics-822292',
            'md5': 'a13ad8bbb45eec4405a45f9bd7ed0356',
            'info_dict': {
                'id': '822292',
                'ext': 'mp4',
                'title': 'Attack The Heart Attack - A Public Awareness Initiative By Medtronics',
                'description': 'md5:31b876e23795b4d7ef91797f88b22730',
                'upload_date': '20240805',
                'duration': 1304,
                'thumbnail': 'https://c.ndtvimg.com/2024-08/kh67tomo_heartattack_640x480_05_August_24.jpg',
            },
        },
        {
            'url': 'https://food.ndtv.com/video-watch-ndtv-food-awards-2024-on-ndtv-24x7-on-saturday-9th-march-2024-767098',
            'md5': '78ddea4f057115e84952563749c6b94c',
            'info_dict': {
                'id': '767098',
                'ext': 'mp4',
                'title': 'Watch NDTV Food Awards 2024 On NDTV 24x7 On Saturday 9th March, 2024',
                'description': 'md5:4a8831a038ab50dc5ea76b1fad4b51d0',
                'upload_date': '20240307',
                'duration': 35,
                'thumbnail': 'https://c.ndtvimg.com/2024-03/2eianfs_food-awards_640x480_08_March_24.jpg',
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

        title = clean_html(self._html_search_meta('taboola:title', webpage, 'title', default=None) or self._html_search_meta('name', webpage, 'title', default=None) or self._og_search_title(webpage))

        # in "movies" sub-site pages, filename is URL
        # in "food" sub-site pages, url string contains escape characters
        video_url = (self._html_search_meta('contentUrl', webpage, 'video-url', default=None)
                     or self._search_regex(r'\"media_mp4\"\s*:\s*\"([^\"]+)\"', webpage, 'video-url')).replace('\\/', '/')

        # "doctor" sub-site has MM:SS format
        duration = parse_duration(self._html_search_meta('video:duration', webpage, 'duration', default=None) or self._search_regex(r'\"dur\"\s*:\s*\"([^\"]+)\"', webpage, 'duration'))

        # "sports", "doctor", "swirlster" sub-sites don't have 'publish-date'
        upload_date = unified_strdate(self._html_search_meta(
            'publish-date', webpage, 'upload date', default=None) or self._html_search_meta(
            'uploadDate', webpage, 'upload date', default=None) or self._search_regex(
            r'datePublished"\s*:\s*"([^"]+)"', webpage, 'upload date', fatal=False))

        description = clean_html(self._html_search_meta('description', webpage, 'description', default=None)
                                 or remove_end(self._og_search_description(webpage), ' (Read more)'))

        thumbnail = (self._html_search_meta('thumbnailUrl', webpage, 'thumbnail', default=None) or self._search_regex(r'\"image\"\s*:\s*\"([^\"]+)\"', webpage, 'thumbnail')).replace('\\/', '/')

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'upload_date': upload_date,
        }
