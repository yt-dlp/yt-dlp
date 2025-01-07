import json
import re
import urllib.parse

from .common import InfoExtractor
from .ninecninemedia import NineCNineMediaIE
from ..utils import extract_attributes, orderedSet
from ..utils.traversal import find_element, traverse_obj


class CTVNewsIE(InfoExtractor):
    _BASE_REGEX = r'https?://(?:[^.]+\.)?ctvnews\.ca/'
    _VIDEO_ID_RE = r'(?P<id>\d{5,})'
    _PLAYLIST_ID_RE = r'(?P<id>\d\.\d{5,})'
    _VALID_URL = [
        rf'{_BASE_REGEX}video/c{_VIDEO_ID_RE}',
        rf'{_BASE_REGEX}video(?:-gallery)?/?\?clipId={_VIDEO_ID_RE}',
        rf'{_BASE_REGEX}video/?\?(?:playlist|bin)Id={_PLAYLIST_ID_RE}',
        rf'{_BASE_REGEX}(?!video/)[^?#]*?{_PLAYLIST_ID_RE}/?(?:$|[?#])',
        rf'{_BASE_REGEX}(?!video/)[^?#]+\?binId={_PLAYLIST_ID_RE}',
    ]
    _TESTS = [{
        'url': 'http://www.ctvnews.ca/video?clipId=901995',
        'md5': 'b608f466c7fa24b9666c6439d766ab7e',
        'info_dict': {
            'id': '901995',
            'ext': 'flv',
            'title': 'Extended: \'That person cannot be me\' Johnson says',
            'description': 'md5:958dd3b4f5bbbf0ed4d045c790d89285',
            'timestamp': 1467286284,
            'upload_date': '20160630',
            'categories': [],
            'season_number': 0,
            'season': 'Season 0',
            'tags': [],
            'series': 'CTV News National | Archive | Stories 2',
            'season_id': '57981',
            'thumbnail': r're:https?://.*\.jpg$',
            'duration': 764.631,
        },
    }, {
        'url': 'https://barrie.ctvnews.ca/video/c3030933-here_s-what_s-making-news-for-nov--15?binId=1272429',
        'md5': '8b8c2b33c5c1803e3c26bc74ff8694d5',
        'info_dict': {
            'id': '3030933',
            'ext': 'flv',
            'title': 'Here’s what’s making news for Nov. 15',
            'description': 'Here are the top stories we’re working on for CTV News at 11 for Nov. 15',
            'thumbnail': 'http://images2.9c9media.com/image_asset/2021_2_22_a602e68e-1514-410e-a67a-e1f7cccbacab_png_2000x1125.jpg',
            'season_id': '58104',
            'season_number': 0,
            'tags': [],
            'season': 'Season 0',
            'categories': [],
            'series': 'CTV News Barrie',
            'upload_date': '20241116',
            'duration': 42.943,
            'timestamp': 1731722452,
        },
    }, {
        'url': 'http://www.ctvnews.ca/video?playlistId=1.2966224',
        'info_dict':
        {
            'id': '1.2966224',
        },
        'playlist_mincount': 19,
    }, {
        'url': 'http://www.ctvnews.ca/video?binId=1.2876780',
        'info_dict':
        {
            'id': '1.2876780',
        },
        'playlist_mincount': 100,
    }, {
        'url': 'https://www.ctvnews.ca/it-s-been-23-years-since-toronto-called-in-the-army-after-a-major-snowstorm-1.5736957',
        'info_dict':
        {
            'id': '1.5736957',
        },
        'playlist_mincount': 6,
    }, {
        'url': 'https://www.ctvnews.ca/business/respondents-to-bank-of-canada-questionnaire-largely-oppose-creating-a-digital-loonie-1.6665797',
        'md5': '24bc4b88cdc17d8c3fc01dfc228ab72c',
        'info_dict': {
            'id': '2695026',
            'ext': 'flv',
            'season_id': '89852',
            'series': 'From CTV News Channel',
            'description': 'md5:796a985a23cacc7e1e2fafefd94afd0a',
            'season': '2023',
            'title': 'Bank of Canada asks public about digital currency',
            'categories': [],
            'tags': [],
            'upload_date': '20230526',
            'season_number': 2023,
            'thumbnail': 'http://images2.9c9media.com/image_asset/2019_3_28_35f5afc3-10f6-4d92-b194-8b9a86f55c6a_png_1920x1080.jpg',
            'timestamp': 1685105157,
            'duration': 253.553,
        },
    }, {
        'url': 'https://stox.ctvnews.ca/video-gallery?clipId=582589',
        'md5': '135cc592df607d29dddc931f1b756ae2',
        'info_dict': {
            'id': '582589',
            'ext': 'flv',
            'categories': [],
            'timestamp': 1427906183,
            'season_number': 0,
            'duration': 125.559,
            'thumbnail': 'http://images2.9c9media.com/image_asset/2019_3_28_35f5afc3-10f6-4d92-b194-8b9a86f55c6a_png_1920x1080.jpg',
            'series': 'CTV News Stox',
            'description': 'CTV original footage of the rise and fall of the Berlin Wall.',
            'title': 'Berlin Wall',
            'season_id': '63817',
            'season': 'Season 0',
            'tags': [],
            'upload_date': '20150401',
        },
    }, {
        'url': 'https://ottawa.ctvnews.ca/features/regional-contact/regional-contact-archive?binId=1.1164587#3023759',
        'md5': 'a14c0603557decc6531260791c23cc5e',
        'info_dict': {
            'id': '3023759',
            'ext': 'flv',
            'season_number': 2024,
            'timestamp': 1731798000,
            'season': '2024',
            'episode': 'Episode 125',
            'description': 'CTV News Ottawa at Six',
            'duration': 2712.076,
            'episode_number': 125,
            'upload_date': '20241116',
            'title': 'CTV News Ottawa at Six for Saturday, November 16, 2024',
            'thumbnail': 'http://images2.9c9media.com/image_asset/2019_3_28_35f5afc3-10f6-4d92-b194-8b9a86f55c6a_png_1920x1080.jpg',
            'categories': [],
            'tags': [],
            'series': 'CTV News Ottawa at Six',
            'season_id': '92667',
        },
    }, {
        'url': 'http://www.ctvnews.ca/1.810401',
        'only_matching': True,
    }, {
        'url': 'http://www.ctvnews.ca/canadiens-send-p-k-subban-to-nashville-in-blockbuster-trade-1.2967231',
        'only_matching': True,
    }, {
        'url': 'http://vancouverisland.ctvnews.ca/video?clipId=761241',
        'only_matching': True,
    }]

    def _ninecninemedia_url_result(self, clip_id):
        return self.url_result(f'9c9media:ctvnews_web:{clip_id}', NineCNineMediaIE, clip_id)

    def _real_extract(self, url):
        page_id = self._match_id(url)

        if mobj := re.fullmatch(self._VIDEO_ID_RE, urllib.parse.urlparse(url).fragment):
            page_id = mobj.group('id')

        if re.fullmatch(self._VIDEO_ID_RE, page_id):
            return self._ninecninemedia_url_result(page_id)

        webpage = self._download_webpage(f'https://www.ctvnews.ca/{page_id}', page_id, query={
            'ot': 'example.AjaxPageLayout.ot',
            'maxItemsPerPage': 1000000,
        })
        entries = [self._ninecninemedia_url_result(clip_id)
                   for clip_id in orderedSet(re.findall(r'clip\.id\s*=\s*(\d+);', webpage))]
        if not entries:
            webpage = self._download_webpage(url, page_id)
            if 'getAuthStates("' in webpage:
                entries = [self._ninecninemedia_url_result(clip_id) for clip_id in
                           self._search_regex(r'getAuthStates\("([\d+,]+)"', webpage, 'clip ids').split(',')]
            else:
                entries = [
                    self._ninecninemedia_url_result(clip_id) for clip_id in
                    traverse_obj(webpage, (
                        {find_element(tag='jasper-player-container', html=True)},
                        {extract_attributes}, 'axis-ids', {json.loads}, ..., 'axisId', {str}))
                ]

        return self.playlist_result(entries, page_id)
