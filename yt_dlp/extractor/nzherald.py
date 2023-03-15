import json

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..compat import compat_str
from ..utils import ExtractorError, traverse_obj


class NZHeraldIE(InfoExtractor):
    IE_NAME = 'nzherald'
    _VALID_URL = r'https?://(?:www\.)?nzherald\.co\.nz/[\w\/-]+\/(?P<id>[A-Z0-9]+)'
    _TESTS = [
        {
            # Video accessible under 'video' key
            'url': 'https://www.nzherald.co.nz/nz/queen-elizabeth-death-nz-public-holiday-announced-for-september-26/CEOPBSXO2JDCLNK3H7E3BIE2FA/',
            'info_dict': {
                'id': '6312191736112',
                'ext': 'mp4',
                'title': 'Focus: PM holds post-Cabinet press conference',
                'duration': 238.08,
                'upload_date': '20220912',
                'uploader_id': '1308227299001',
                'timestamp': 1662957159,
                'tags': [],
                'thumbnail': r're:https?://.*\.jpg$',
                'description': 'md5:2f17713fcbfcfbe38bb9e7dfccbb0f2e',
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
                'description': 'md5:d361aaa0c6498f7ac1bc4fc0a0aec1e4',
                'thumbnail': r're:https?://.*\.jpg$',
                'tags': ['travel', 'video'],
                'duration': 43.627,
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
            },
            'skip': 'video removed',
        }, {
            # customVideo embed requiring additional API call
            'url': 'https://www.nzherald.co.nz/nz/politics/reserve-bank-rejects-political-criticisms-stands-by-review/2JO5Q4WLZRCBBNWTLACZMOP4RA/',
            'info_dict': {
                'id': '6315123873112',
                'ext': 'mp4',
                'timestamp': 1667862725,
                'title': 'Focus: Luxon on re-appointment of Reserve Bank governor Adrian Orr',
                'upload_date': '20221107',
                'description': 'md5:df2f1f7033a8160c66e28e4743f5d934',
                'uploader_id': '1308227299001',
                'tags': ['video', 'nz herald focus', 'politics', 'politics videos'],
                'thumbnail': r're:https?://.*\.jpg$',
                'duration': 99.584,
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

    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/1308227299001/S1BXZn8t_default/index.html?videoId=%s'

    def _extract_bc_embed_url(self, webpage):
        """The initial webpage may include the brightcove player embed url"""
        bc_url = BrightcoveNewIE._extract_url(self, webpage)
        return bc_url or self._search_regex(
            r'(?:embedUrl)\"\s*:\s*\"(?P<embed_url>%s)' % BrightcoveNewIE._VALID_URL,
            webpage, 'embed url', default=None, group='embed_url')

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)
        bc_url = self._extract_bc_embed_url(webpage)

        if not bc_url:
            fusion_metadata = self._parse_json(
                self._search_regex(r'Fusion\.globalContent\s*=\s*({.+?})\s*;', webpage, 'fusion metadata'), article_id)

            video_metadata = fusion_metadata.get('video')
            if not video_metadata:
                custom_video_id = traverse_obj(fusion_metadata, ('customVideo', 'embed', 'id'), expected_type=str)
                if custom_video_id:
                    video_metadata = self._download_json(
                        'https://www.nzherald.co.nz/pf/api/v3/content/fetch/full-content-by-id', article_id,
                        query={'query': json.dumps({'id': custom_video_id, 'site': 'nzh'}), '_website': 'nzh'})
            bc_video_id = traverse_obj(
                video_metadata or fusion_metadata,  # fusion metadata is the video metadata for video-only pages
                'brightcoveId', ('content_elements', ..., 'referent', 'id'),
                get_all=False, expected_type=compat_str)

            if not bc_video_id:
                if isinstance(video_metadata, dict) and len(video_metadata) == 0:
                    raise ExtractorError('This article does not have a video.', expected=True)
                else:
                    raise ExtractorError('Failed to extract brightcove video id')
            bc_url = self.BRIGHTCOVE_URL_TEMPLATE % bc_video_id

        return self.url_result(bc_url, 'BrightcoveNew')
