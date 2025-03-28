from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
    urljoin,
)


class EuropaIE(InfoExtractor):
    _VALID_URL = r'https?://audiovisual\.ec\.europa\.eu/(?P<language>[^/]*)/video/(?P<id>[A-Za-z0-9-]+)'
    _FORMATS = {
        'lr': {'vcodec': 'h264', 'acodec': 'aac', 'height': 480},
        'hdmp4': {'vcodec': 'h264', 'acodec': 'aac', 'height': 1080},
        'mp3': {'vcodec': 'none', 'acodec': 'mp3', 'abr': 128},
    }
    _TESTS = [{
        'url': 'https://audiovisual.ec.europa.eu/en/video/I-107758',
        'md5': '728cca2fd41d5aa7350cec1141fbe620',
        'info_dict': {
            'id': 'I-107758',
            'ext': 'mp4',
            'title': 'TRADE - Wikileaks on TTIP:- Q&A',
            'description': 'LIVE EC Midday press briefing of 11/08/2015',
            'uploader': 'beluga',
            'duration': 34.92,
            'thumbnail': 'https://vod.prd.commavservices.eu/18/107758/THUMB_M_I107758INT1W.jpg',
            'timestamp': 1439288640,
            'upload_date': '20150811',
            'modified_timestamp': 1731858348,
            'modified_date': '20241117',
        },
    }, {
        'url': 'https://audiovisual.ec.europa.eu/en/video/I-107786',
        'md5': '5ecf1eb72800573ed75a53fc06511967',
        'info_dict': {
            'id': 'I-107786',
            'ext': 'mp4',
            'title': 'Midday press briefing from 14/08/2015',
            'description': 'md5:e56082f090a0ad1da6b76f453dd9d155',
            'uploader': 'beluga',
            'thumbnail': 'https://vod.prd.commavservices.eu/06/107786/THUMB_M_I107786INT1W.jpg',
            'timestamp': 1439503200,
            'upload_date': '20150813',
            'modified_timestamp': 1731858616,
            'modified_date': '20241117',
        },
    }, {
        'url': 'https://audiovisual.ec.europa.eu/en/video/I-109295',
        'md5': '3a6d560e0aff5633de4bb7cdc368ab72',
        'info_dict': {
            'id': 'I-109295',
            'ext': 'mp4',
            'title': 'md5:dfc882adaabf388999e20d3079ee5277',
            'description': 'md5:67374bddab3fd2a8a319a92e1a286ad2',
            'uploader': 'beluga',
            'thumbnail': 'https://vod.prd.commavservices.eu/15/109295/THUMB_M_I109295INT1W_03.jpg',
            'timestamp': 1443762000,
            'upload_date': '20151002',
            'modified_timestamp': 1731845416,
            'modified_date': '20241117',
        },
    }]

    def _real_extract(self, url):
        language, video_id = self._match_valid_url(url).group('language', 'id')
        constants = self._download_webpage('https://audiovisual.ec.europa.eu/js/constants.js', video_id, 'Downloading constants')
        api = self._search_regex(r'"urlJellyfishApi":\s*"([^"]+)"', constants, 'urlJellyfishApi', 'https://yy2iyrkool.execute-api.eu-west-1.amazonaws.com/jellyfish/')
        media = self._download_json(urljoin(api, f'medias/{video_id}'), video_id, 'Downloading media JSON')
        info = traverse_obj(media, ('latest', {
            'modified_timestamp': ('timestamp', {parse_iso8601}),
            'uploader': ('user', {str_or_none}),
            'id': ('data', 'reference', {str_or_none}),
            'duration': ('data', 'duration', {lambda d: None if d == 1 else d}),
            'timestamp': ('data', 'productionDatetime', {parse_iso8601}),
            'title': ('data', 'titles', ..., ..., {lambda t: t and t.strip()}, any),
            'description': ('data', 'summaries', ..., ..., {lambda t: t and t.strip()}, any),
            'thumbnails': ('data', 'files', ..., ('image', 'thumb'), {'url': ('url', {url_or_none})}),
        }))
        formats = []

        for file in traverse_obj(media, ('latest', 'data', 'files', ...)):
            l = traverse_obj(file, ('language', {lambda l: l and l.lower()}))
            for k in ('mp3', 'lr', 'hdmp4'):
                if f_url := traverse_obj(file, (k, 'url')):
                    formats.append({
                        'url': f_url,
                        'language': l,
                        'language_preference': 10 if (l and l.lower() == language) or l == 'int' else -10,
                        'format_id': f'{k}-{l}',
                        **self._FORMATS[k],
                    })
        return {**info, 'formats': formats}


class EuroParlWebstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://multimedia\.europarl\.europa\.eu/
        (?:\w+/)?webstreaming/(?:[\w-]+_)?(?P<id>[\w-]+)
    '''
    _TESTS = [{
        'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/plenary-session_20220914-0900-PLENARY',
        'info_dict': {
            'id': '62388b15-d85b-4add-99aa-ba12ccf64f0d',
            'display_id': '20220914-0900-PLENARY',
            'ext': 'mp4',
            'title': 'Plenary session',
            'release_timestamp': 1663139069,
            'release_date': '20220914',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # live webstream
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/euroscola_20221115-1000-SPECIAL-EUROSCOLA',
        'info_dict': {
            'ext': 'mp4',
            'id': '510eda7f-ba72-161b-7ee7-0e836cd2e715',
            'release_timestamp': 1668502800,
            'title': 'Euroscola 2022-11-15 19:21',
            'release_date': '20221115',
            'live_status': 'is_live',
        },
        'skip': 'not live anymore',
    }, {
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/committee-on-culture-and-education_20230301-1130-COMMITTEE-CULT',
        'info_dict': {
            'id': '7355662c-8eac-445e-4bb9-08db14b0ddd7',
            'display_id': '20230301-1130-COMMITTEE-CULT',
            'ext': 'mp4',
            'release_date': '20230301',
            'title': 'Committee on Culture and Education',
            'release_timestamp': 1677666641,
        },
    }, {
        # live stream
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/committee-on-environment-public-health-and-food-safety_20230524-0900-COMMITTEE-ENVI',
        'info_dict': {
            'id': 'e4255f56-10aa-4b3c-6530-08db56d5b0d9',
            'ext': 'mp4',
            'release_date': '20230524',
            'title': r're:Committee on Environment, Public Health and Food Safety \d{4}-\d{2}-\d{2}\s\d{2}:\d{2}',
            'release_timestamp': 1684911541,
            'live_status': 'is_live',
        },
        'skip': 'Not live anymore',
    }, {
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/20240320-1345-SPECIAL-PRESSER',
        'info_dict': {
            'id': 'c1f11567-5b52-470a-f3e1-08dc3c216ace',
            'display_id': '20240320-1345-SPECIAL-PRESSER',
            'ext': 'mp4',
            'release_date': '20240320',
            'title': 'md5:7c6c814cac55dea5e2d87bf8d3db2234',
            'release_timestamp': 1710939767,
        },
    }, {
        'url': 'https://multimedia.europarl.europa.eu/webstreaming/briefing-for-media-on-2024-european-elections_20240429-1000-SPECIAL-OTHER',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        webpage_nextjs = self._search_nextjs_data(webpage, display_id)['props']['pageProps']

        json_info = self._download_json(
            'https://acs-api.europarl.connectedviews.eu/api/FullMeeting', display_id,
            query={
                'api-version': 1.0,
                'tenantId': 'bae646ca-1fc8-4363-80ba-2c04f06b4968',
                'externalReference': display_id,
            })

        formats, subtitles = [], {}
        for hls_url in traverse_obj(json_info, ((('meetingVideo'), ('meetingVideos', ...)), 'hlsUrl')):
            fmt, subs = self._extract_m3u8_formats_and_subtitles(hls_url, display_id)
            formats.extend(fmt)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': json_info['id'],
            'display_id': display_id,
            'title': traverse_obj(webpage_nextjs, (('mediaItem', 'title'), ('title', )), get_all=False),
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': parse_iso8601(json_info.get('startDateTime')),
            'is_live': traverse_obj(webpage_nextjs, ('mediaItem', 'mediaSubType')) == 'Live',
        }
