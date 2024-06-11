import json
import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    traverse_obj,
    try_call,
    unescapeHTML,
    unified_timestamp,
)


class HRFernsehenIE(InfoExtractor):
    IE_NAME = 'hrfernsehen'
    _VALID_URL = r'^https?://www\.(?:hr-fernsehen|hessenschau)\.de/.*,video-(?P<id>[0-9]{6})\.html'
    _TESTS = [{
        'url': 'https://www.hessenschau.de/tv-sendung/hessenschau-vom-26082020,video-130546.html',
        'md5': '5c4e0ba94677c516a2f65a84110fc536',
        'info_dict': {
            'id': '130546',
            'ext': 'mp4',
            'description': 'Sturmtief Kirsten fegt über Hessen / Die Corona-Pandemie – eine Chronologie / '
                           'Sterbehilfe: Die Lage in Hessen / Miss Hessen leitet zwei eigene Unternehmen / '
                           'Pop-Up Museum zeigt Schwarze Unterhaltung und Black Music',
            'subtitles': {'de': [{
                'url': 'https://hr-a.akamaihd.net/video/as/hessenschau/2020_08/hrLogo_200826200407_L385592_512x288-25p-500kbit.vtt',
            }]},
            'timestamp': 1598400000,
            'upload_date': '20200826',
            'thumbnail': 'https://www.hessenschau.de/tv-sendung/hs_ganz-1554~_t-1598465545029_v-16to9.jpg',
            'title': 'hessenschau vom 26.08.2020',
            'duration': 1654,
        },
    }, {
        'url': 'https://www.hr-fernsehen.de/sendungen-a-z/mex/sendungen/fair-und-gut---was-hinter-aldis-eigenem-guetesiegel-steckt,video-130544.html',
        'only_matching': True,
    }]

    _GEO_COUNTRIES = ['DE']

    def extract_formats(self, loader_data):
        stream_formats = []
        data = loader_data['mediaCollection']['streams'][0]['media']
        for inner in data[1:]:
            stream_format = {
                'format_id': try_call(lambda: f'{inner["maxHResolutionPx"]}p'),
                'height': inner.get('maxHResolutionPx'),
                'url': inner['url'],
            }

            quality_information = re.search(r'([0-9]{3,4})x([0-9]{3,4})-([0-9]{2})p-([0-9]{3,4})kbit',
                                            inner['url'])
            if quality_information:
                stream_format['width'] = int_or_none(quality_information.group(1))
                stream_format['height'] = int_or_none(quality_information.group(2))
                stream_format['fps'] = int_or_none(quality_information.group(3))
                stream_format['tbr'] = int_or_none(quality_information.group(4))

            stream_formats.append(stream_format)
        return stream_formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_meta(
            ['og:title', 'twitter:title', 'name'], webpage)
        description = self._html_search_meta(
            ['description'], webpage)

        loader_str = unescapeHTML(self._search_regex(r"data-(?:new-)?hr-mediaplayer-loader='([^']*)'", webpage, 'ardloader'))
        loader_data = json.loads(loader_str)

        subtitle = traverse_obj(loader_data, ('mediaCollection', 'subTitles', 0, 'sources', 0, 'url'))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': self.extract_formats(loader_data),
            'subtitles': {'de': [{'url': subtitle}]},
            'timestamp': unified_timestamp(self._search_regex(
                r'<time\sdatetime="(\d{4}\W\d{1,2}\W\d{1,2})', webpage, 'datetime', fatal=False)),
            'duration': int_or_none(traverse_obj(
                loader_data, ('playerConfig', 'pluginData', 'trackingAti@all', 'richMedia', 'duration'))),
            'thumbnail': self._search_regex(r'thumbnailUrl\W*([^"]+)', webpage, 'thumbnail', default=None),
        }
