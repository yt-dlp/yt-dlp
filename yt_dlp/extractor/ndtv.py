
from .common import InfoExtractor
from ..utils import clean_html, determine_ext, parse_duration, traverse_obj, unescapeHTML, unified_strdate


class NDTVIE(InfoExtractor):
    _WORKING = True
    _VALID_URL = r'https?://(?:[^/]+\.)?ndtv\.com/(?:[^/]+/)*videos?/?(?:[^/]+/)*[^/?^&]+-(?P<id>\d+)'

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
                'duration': 2218,
                'thumbnail': r're:https?://.*\.jpg',
                'categories': 'shows',
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
                'upload_date': '20171019',
                'duration': 137,
                'thumbnail': r're:https?://.*\.jpg',
                'categories': 'entertainment',
                'channel_id': '1',
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
                'categories': 'entertainment',
                'channel_id': '1',
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
                'categories': 'news',
                'channel_id': '1',
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
                'categories': 'fangully',
                'channel_id': '',
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
                'categories': 'Health',
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
                'duration': 35,
                'thumbnail': 'https://c.ndtvimg.com/2024-03/2eianfs_food-awards_640x480_08_March_24.jpg',
                'categories': 'food',
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

        data = self._search_json(r'__html5playerdata\s*=\s*', webpage, 'json_data', video_id)

        title = clean_html(unescapeHTML(traverse_obj(data, ('title'))))
        duration = parse_duration(traverse_obj(data, ('dur')))
        upload_date = unified_strdate(traverse_obj(data, ('date')))
        video_m3u8 = traverse_obj(data, ('media'))
        video_mp4 = traverse_obj(data, ('media_mp4'))
        video_webm = traverse_obj(data, ('media_webm'))
        description = clean_html(unescapeHTML(traverse_obj(data, ('description'))))
        thumbnail = traverse_obj(data, ('image'))
        channel_id = traverse_obj(data, ('channel'))
        categories = traverse_obj(data, ('category'))

        formats = []
        if video_mp4:
            formats.append({'url': video_mp4, 'ext': determine_ext(video_mp4)})
        if video_webm:
            formats.append({'url': video_webm, 'ext': determine_ext(video_webm)})
        if video_m3u8:
            m3u8_data = self._extract_m3u8_formats(video_m3u8, video_id)
            formats.extend(m3u8_data)
            # here, making the assumption that mp4 video available is always the highest quality
            # will update if any deviation found
            formats[0]['width'] = m3u8_data[-1]['width']
            formats[0]['height'] = m3u8_data[-1]['height']
            formats[0]['tbr'] = m3u8_data[-1]['tbr']

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'upload_date': upload_date,
            'categories': categories,
            'channel_id': channel_id,
        }
