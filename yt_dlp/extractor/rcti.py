# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    str_or_none
)


class RCTIPlusIE(InfoExtractor):
    _VALID_URL = r'https://www\.rctiplus\.com/programs/\d+?/.*?/episode/(?P<id>\d+)/(?P<display_id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.rctiplus.com/programs/540/upin-ipin/episode/5642/esok-puasa-upin-ipin-ep1',
        'md5': 'e9b7c88101aab04d9115e2718dae7260',
        'info_dict': {
            'id': '5642',
            'title': 'Esok Puasa - Upin & Ipin Ep.1',
            'ext': 'm3u8',
        },
        'params': {
            'format': 'bestvideo, bestaudio',
        },
    }

    _AUTH_KEY = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ2aWQiOjAsInRva2VuIjoiMzZkNDVhOTFiYTgzNjcxMiIsInBsIjoiYW5kcm9pZCIsImRldmljZV9pZCI6IjJjZjk5NzMwNWJiM2ZkYzcifQ.V5m4mAzRyzNiCaEan9kOn5CZO3dyYfjYuFNYTHGxgyA'

    def _call_api(self, url, video_id, note=None):
        json = self._download_json(
            url, video_id, note=note, headers={'Authorization': self._AUTH_KEY})
        if json.get('status', {}).get('code') != 0:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, json["status"]["message_client"]))
        return json.get('data'), json.get('meta')

    def _real_extract(self, url):
        video_id, display_id = re.match(self._VALID_URL, url).groups()
        webpage = self._download_webpage(url, display_id)

        try:
            self._AUTH_KEY = self._search_regex(
                r'\'Authorization\':"(?P<auth>[^"]+)"', webpage, 'auth-key')
        except RegexNotFoundError:
            pass

        video_json,_ = self._call_api(
            'https://api.rctiplus.com/api/v1/episode/%s/url?appierid=.1' % video_id, display_id, 'Downloading video URL JSON')
        video_url = video_json.get('url')

        video_meta, meta_paths = self._call_api(
            'https://api.rctiplus.com/api/v1/episode/' + video_id, display_id, 'Downloading video metadata JSON')

        thumbnails, image_path = [], meta_paths.get('image_path', 'https://rstatic.akamaized.net/media/')
        if video_meta.get('portrait_image'):
            thumbnails.append({
                'id': 'portrait_image',
                'url': image_path + '2000' + video_meta['portrait_image']
            })
        if video_meta.get('landscape_image'):
            thumbnails.append({
                'id': 'landscape_image',
                'url': image_path + '2000' + video_meta['landscape_image']
            })

        formats = self._extract_m3u8_formats(video_url, display_id)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_meta.get('title'),
            'description': video_meta.get('summary'),
            'timestamp': video_meta.get('release_date'),
            'duration': video_meta.get('duration'),
            'average_rating': video_meta.get('star_rating'),
            'series': video_meta.get('program_title'),
            'season_number': video_meta.get('season'),
            'episode_number': video_meta.get('episode'),
            'categories': [video_meta.get('genre')],
            'formats': formats,
            'thumbnails': thumbnails
        }
