# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    HEADRequest,
    parse_age_limit,
    parse_iso8601,
    # smuggle_url,
)


class TenPlayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?10play\.com\.au/(?:[^/]+/)+(?P<id>tpv\d{6}[a-z]{5})'
    _TESTS = [{
        'url': 'https://10play.com.au/masterchef/episodes/season-1/masterchef-s1-ep-1/tpv190718kwzga',
        'info_dict': {
            'id': '6060533435001',
            'ext': 'mp4',
            'title': 'MasterChef - S1 Ep. 1',
            'description': 'md5:4fe7b78e28af8f2d900cd20d900ef95c',
            'age_limit': 10,
            'timestamp': 1240828200,
            'upload_date': '20090427',
            'uploader_id': '2199827728001',
        },
        'params': {
            # 'format': 'bestvideo',
            'skip_download': True,
        }
    }, {
        'url': 'https://10play.com.au/how-to-stay-married/web-extras/season-1/terrys-talks-ep-1-embracing-change/tpv190915ylupc',
        'only_matching': True,
    }]
    # BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/2199827728001/cN6vRtRQt_default/index.html?videoId=%s'
    _GEO_BYPASS = False
    _FASTLY_URL_TEMPL = 'https://10-selector.global.ssl.fastly.net/s/kYEXFC/media/%s?mbr=true&manifest=m3u&format=redirect'

    def _real_extract(self, url):
        content_id = self._match_id(url)
        data = self._download_json(
            'https://10play.com.au/api/video/' + content_id, content_id)
        video = data.get('video') or {}
        metadata = data.get('metaData') or {}
        brightcove_id = video.get('videoId') or metadata['showContentVideoId']
        # brightcove_url = smuggle_url(
        #     self.BRIGHTCOVE_URL_TEMPLATE % brightcove_id,
        #     {'geo_countries': ['AU']})
        m3u8_url = self._request_webpage(HEADRequest(
            self._FASTLY_URL_TEMPL % brightcove_id), brightcove_id).geturl()
        if '10play-not-in-oz' in m3u8_url:
            self.raise_geo_restricted(countries=['AU'])
        formats = self._extract_m3u8_formats(m3u8_url, brightcove_id, 'mp4')
        self._sort_formats(formats)

        return {
            # '_type': 'url_transparent',
            # 'url': brightcove_url,
            'formats': formats,
            'id': brightcove_id,
            'title': video.get('title') or metadata.get('pageContentName') or metadata['showContentName'],
            'description': video.get('description'),
            'age_limit': parse_age_limit(video.get('showRatingClassification') or metadata.get('showProgramClassification')),
            'series': metadata.get('showName'),
            'season': metadata.get('showContentSeason'),
            'timestamp': parse_iso8601(metadata.get('contentPublishDate') or metadata.get('pageContentPublishDate')),
            'thumbnail': video.get('poster'),
            'uploader_id': '2199827728001',
            # 'ie_key': 'BrightcoveNew',
        }
