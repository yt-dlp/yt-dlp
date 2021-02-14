# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    js_to_json,
    url_or_none,
)


class APAIE(InfoExtractor):
    _VALID_URL = r'https?://[^/]+\.apa\.at/embed/(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'
    _TESTS = [{
        'url': 'http://uvp.apa.at/embed/293f6d17-692a-44e3-9fd5-7b178f3a1029',
        'md5': '2b12292faeb0a7d930c778c7a5b4759b',
        'info_dict': {
            'id': 'jjv85FdZ',
            'ext': 'mp4',
            'title': '"Blau ist mysteriös": Die Blue Man Group im Interview',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 254,
            'timestamp': 1519211149,
            'upload_date': '20180221',
        },
    }, {
        'url': 'https://uvp-apapublisher.sf.apa.at/embed/2f94e9e6-d945-4db2-9548-f9a41ebf7b78',
        'only_matching': True,
    }, {
        'url': 'http://uvp-rma.sf.apa.at/embed/70404cca-2f47-4855-bbb8-20b1fae58f76',
        'only_matching': True,
    }, {
        'url': 'http://uvp-kleinezeitung.sf.apa.at/embed/f1c44979-dba2-4ebf-b021-e4cf2cac3c81',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return [
            mobj.group('url')
            for mobj in re.finditer(
                r'<iframe[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//[^/]+\.apa\.at/embed/[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}.*?)\1',
                webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        jwplatform_id = self._search_regex(
            r'media[iI]d\s*:\s*["\'](?P<id>[a-zA-Z0-9]{8})', webpage,
            'jwplatform id', default=None)

        if jwplatform_id:
            return self.url_result(
                'jwplatform:' + jwplatform_id, ie='JWPlatform',
                video_id=video_id)

        sources = self._parse_json(
            self._search_regex(
                r'sources\s*=\s*(\[.+?\])\s*;', webpage, 'sources'),
            video_id, transform_source=js_to_json)

        formats = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            source_url = url_or_none(source.get('file'))
            if not source_url:
                continue
            ext = determine_ext(source_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    source_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': source_url,
                })
        self._sort_formats(formats)

        thumbnail = self._search_regex(
            r'image\s*:\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage,
            'thumbnail', fatal=False, group='url')

        return {
            'id': video_id,
            'title': video_id,
            'thumbnail': thumbnail,
            'formats': formats,
        }
