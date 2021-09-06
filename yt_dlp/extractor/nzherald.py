# coding: utf-8
from __future__ import unicode_literals

from .brightcove import BrightcoveNewIE
from ..compat import compat_str
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    urljoin
)


class NZHeraldIE(InfoExtractor):
    IE_NAME = 'nzherald'
    _VALID_URL = r'https?://(?:www\.)?nzherald\.co\.nz/[\w\/-]+\/(?P<id>[A-Z0-9]+)'
    _TESTS = [
        {
            'url': 'https://www.nzherald.co.nz/nz/weather-heavy-rain-gales-across-nz-most-days-this-week/PTG7QWY4E2225YHZ5NAIRBTYTQ/',
            'info_dict': {
                'id': '6271084466001',
                'ext': 'mp4',
                'title': 'MetService severe weather warning: September 6th - 7th',
                'timestamp': 1630891576,
                'upload_date': '20210906',
                'uploader_id': '1308227299001',
                'description': 'md5:db6ca335a22e2cdf37ab9d2bcda52902'
            }

        }, {
            # Webpage has brightcove embed player url
            'url': 'https://www.nzherald.co.nz/travel/pencarrow-coastal-trail/HDVTPJEPP46HJ2UEMK4EGD2DFI/',
            'info_dict': {
                'id': '6261791733001',
                'ext': 'mp4',
                'title': 'Pencarrow Coastal Trail',
                'timestamp': 1625102897,
                'upload_date': '20210701',
                'uploader_id': '1308227299001',
                'description': 'md5:d361aaa0c6498f7ac1bc4fc0a0aec1e4'
            }

        }, {
            # two video embeds of the same video
            'url': 'https://www.nzherald.co.nz/nz/truck-driver-captured-cutting-off-motorist-on-state-highway-1-in-canterbury/FIHNJB7PLLPHWQPK4S7ZBDUC4I/',
            'info_dict': {
                'id': '6251114530001',
                'ext': 'mp4',
                'title': 'Truck travelling north from Rakaia runs car off road',
                'timestamp': 1619730509,
                'upload_date': '20210429',
                'uploader_id': '1308227299001',
                'description': 'md5:4cae7dfb7613ac4c73b9e73a75c6b5d7'
            }
        }, {
            'url': 'https://www.nzherald.co.nz/kahu/kaupapa-companies-my-taiao-supporting-maori-in-study-and-business/PQBO2J25WCG77VGRX7W7BVYEAI/',
            'only_matching': True
        }, {
            'url': 'https://nzherald.co.nz/the-country/video/focus-nzs-first-mass-covid-19-vaccination-event/N5I7IL3BRFLZSD33TLDLYJDGK4/',
            'only_matching': True
        }, {
            'url': 'https://www.nzherald.co.nz/the-vision-is-clear/news/tvic-damian-roper-planting-trees-an-addiction/AN2AAEPNRK5VLISDWQAJZB6ATQ',
            'only_matching': True
        }
    ]

    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'
    BRIGHTCOVE_ACCOUNT_ID = '1308227299001'
    BRIGHTCOVE_PLAYER_ID = 'default'
    FUSION_REACT_JS = 'https://www.nzherald.co.nz/pf/dist/engine/react.js'

    def _extract_bc_details(self, webpage, video_id):
        react_js_url = self._html_search_regex(
            r'<script\b[^>]+id=\"fusion-engine-react-script\"[^>]+src=\"([^\"]+)', webpage, 'Fusion react.js',
            fatal=False)
        react_js = self._download_webpage(
            urljoin('https://www.nzherald.co.nz', react_js_url) or self.FUSION_REACT_JS,
            video_id, note='Downloading Fusion react.js', fatal=False)
        bc_account_id = bc_player_id = None
        if react_js:
            bc_account_id = self._search_regex(
                r'(?:BC_ACCOUNT_ID)\s*:\s*\"([\d]+)', react_js, 'brightcove account id', fatal=False)
            bc_player_id = self._search_regex(
                r'(?:BC_PLAYER_ID)\s*:\s*\"([^\"]+)', react_js, 'brightcove player id', fatal=False)
        return bc_account_id or self.BRIGHTCOVE_ACCOUNT_ID, bc_player_id or self.BRIGHTCOVE_PLAYER_ID

    def _extract_bc_embed(self, webpage):
        """The initial webpage may include the brightcove player embed url"""
        bc_url = BrightcoveNewIE._extract_url(self, webpage)
        if not bc_url:
            return self._search_regex(
                r'(?:embedUrl)\"\s*:\s*\"(?P<embed_url>(%s)[^\"]+)' % BrightcoveNewIE._VALID_URL,
                webpage, 'embed url', default=None)

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)
        bc_url = self._extract_bc_embed(webpage)

        if not bc_url:
            fusion_metadata = self._parse_json(
                self._search_regex(r'Fusion\.globalContent\s*=\s*({.+?})\s*;', webpage, 'fusion metadata'), article_id)

            bc_video_id = traverse_obj(
                fusion_metadata.get('video') or fusion_metadata,
                'brightcoveId', ('content_elements', ..., 'referent', 'id'),
                get_all=False, expected_type=compat_str)

            if not bc_video_id:
                raise ExtractorError('Failed to extract brightcove video id')
            bc_url = self.BRIGHTCOVE_URL_TEMPLATE % (*self._extract_bc_details(webpage, bc_video_id), bc_video_id)

        return self.url_result(bc_url, 'BrightcoveNew')
