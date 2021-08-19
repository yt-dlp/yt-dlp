# coding: utf-8
from __future__ import unicode_literals

import json
import re

from ..utils import int_or_none, unified_timestamp, unescapeHTML
from .common import InfoExtractor


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
                'url': 'https://hr-a.akamaihd.net/video/as/hessenschau/2020_08/hrLogo_200826200407_L385592_512x288-25p-500kbit.vtt'
            }]},
            'timestamp': 1598470200,
            'upload_date': '20200826',
            'thumbnails': [{
                'url': 'https://www.hessenschau.de/tv-sendung/hs_ganz-1554~_t-1598465545029_v-16to9.jpg',
                'id': '0'
            }, {
                'url': 'https://www.hessenschau.de/tv-sendung/hs_ganz-1554~_t-1598465545029_v-16to9__medium.jpg',
                'id': '1'
            }],
            'title': 'hessenschau vom 26.08.2020'
        }
    }, {
        'url': 'https://www.hr-fernsehen.de/sendungen-a-z/mex/sendungen/fair-und-gut---was-hinter-aldis-eigenem-guetesiegel-steckt,video-130544.html',
        'only_matching': True
    }]

    _GEO_COUNTRIES = ['DE']

    def extract_airdate(self, loader_data):
        airdate_str = loader_data.get('mediaMetadata', {}).get('agf', {}).get('airdate')

        if airdate_str is None:
            return None

        return unified_timestamp(airdate_str)

    def extract_formats(self, loader_data):
        stream_formats = []
        for stream_obj in loader_data["videoResolutionLevels"]:
            stream_format = {
                'format_id': str(stream_obj['verticalResolution']) + "p",
                'height': stream_obj['verticalResolution'],
                'url': stream_obj['url'],
            }

            quality_information = re.search(r'([0-9]{3,4})x([0-9]{3,4})-([0-9]{2})p-([0-9]{3,4})kbit',
                                            stream_obj['url'])
            if quality_information:
                stream_format['width'] = int_or_none(quality_information.group(1))
                stream_format['height'] = int_or_none(quality_information.group(2))
                stream_format['fps'] = int_or_none(quality_information.group(3))
                stream_format['tbr'] = int_or_none(quality_information.group(4))

            stream_formats.append(stream_format)

        self._sort_formats(stream_formats)
        return stream_formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_meta(
            ['og:title', 'twitter:title', 'name'], webpage)
        description = self._html_search_meta(
            ['description'], webpage)

        loader_str = unescapeHTML(self._search_regex(r"data-hr-mediaplayer-loader='([^']*)'", webpage, "ardloader"))
        loader_data = json.loads(loader_str)

        info = {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': self.extract_formats(loader_data),
            'timestamp': self.extract_airdate(loader_data)
        }

        if "subtitle" in loader_data:
            info["subtitles"] = {"de": [{"url": loader_data["subtitle"]}]}

        thumbnails = list(set([t for t in loader_data.get("previewImageUrl", {}).values()]))
        if len(thumbnails) > 0:
            info["thumbnails"] = [{"url": t} for t in thumbnails]

        return info
