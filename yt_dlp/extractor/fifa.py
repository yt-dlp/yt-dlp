from .common import InfoExtractor
from ..utils import (
    int_or_none,
    traverse_obj,
    unified_timestamp,
)


class FifaIE(InfoExtractor):
    _VALID_URL = r'https?://www\.fifa\.com/fifaplus/\w{2}/watch/([^#?]+/)?(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.fifa.com/fifaplus/en/watch/7on10qPcnyLajDDU3ntg6y',
        'info_dict': {
            'id': '7on10qPcnyLajDDU3ntg6y',
            'title': 'Italy v France | Final | 2006 FIFA World Cup Germany™ | Full Match Replay',
            'description': 'md5:f4520d0ee80529c8ba4134a7d692ff8b',
            'ext': 'mp4',
            'categories': ['FIFA Tournaments'],
            'thumbnail': 'https://digitalhub.fifa.com/transform/135e2656-3a51-407b-8810-6c34bec5b59b/FMR_2006_Italy_France_Final_Hero',
            'duration': 8165,
            'release_timestamp': 1152403200,
            'release_date': '20060709',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.fifa.com/fifaplus/pt/watch/1cg5r5Qt6Qt12ilkDgb1sV',
        'info_dict': {
            'id': '1cg5r5Qt6Qt12ilkDgb1sV',
            'title': 'Brazil v Germany | Semi-finals | 2014 FIFA World Cup Brazil™ | Extended Highlights',
            'description': 'md5:d908c74ee66322b804ae2e521b02a855',
            'ext': 'mp4',
            'categories': ['FIFA Tournaments', 'Highlights'],
            'thumbnail': 'https://digitalhub.fifa.com/transform/d8fe6f61-276d-4a73-a7fe-6878a35fd082/FIFAPLS_100EXTHL_2014BRAvGER_TMB',
            'duration': 902,
            'release_timestamp': 1404777600,
            'release_date': '20140708',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.fifa.com/fifaplus/fr/watch/3C6gQH9C2DLwzNx7BMRQdp',
        'info_dict': {
            'id': '3C6gQH9C2DLwzNx7BMRQdp',
            'title': 'Josimar goal against Northern Ireland | Classic Goals',
            'description': 'md5:cbe7e7bb52f603c9f1fe9a4780fe983b',
            'ext': 'mp4',
            'categories': ['FIFA Tournaments', 'Goal'],
            'duration': 28,
            'thumbnail': 'https://digitalhub.fifa.com/transform/f9301391-f8d9-48b5-823e-c093ac5e3e11/CG_MEN_1986_JOSIMAR',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        preconnect_link = self._search_regex(
            r'<link\b[^>]+\brel\s*=\s*"preconnect"[^>]+href\s*=\s*"([^"]+)"', webpage, 'Preconnect Link')

        video_details = self._download_json(
            f'{preconnect_link}/sections/videoDetails/{video_id}', video_id, 'Downloading Video Details', fatal=False)

        preplay_parameters = self._download_json(
            f'{preconnect_link}/videoPlayerData/{video_id}', video_id, 'Downloading Preplay Parameters')['preplayParameters']

        content_data = self._download_json(
            'https://content.uplynk.com/preplay/{contentId}/multiple.json?{queryStr}&sig={signature}'.format(**preplay_parameters),
            video_id, 'Downloading Content Data')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(content_data['playURL'], video_id)

        return {
            'id': video_id,
            'title': video_details.get('title'),
            'description': video_details.get('description'),
            'duration': int_or_none(video_details.get('duration')),
            'release_timestamp': unified_timestamp(video_details.get('dateOfRelease')),
            'categories': traverse_obj(video_details, (('videoCategory', 'videoSubcategory'),)),
            'thumbnail': traverse_obj(video_details, ('backgroundImage', 'src')),
            'formats': formats,
            'subtitles': subtitles,
        }
