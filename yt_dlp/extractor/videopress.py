# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    float_or_none,
    parse_age_limit,
    qualities,
    random_birthday,
    try_get,
    unified_timestamp,
    urljoin,
)


class VideoPressIE(InfoExtractor):
    _VALID_URL = r'https?://videopress\.com/embed/(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        'url': 'https://videopress.com/embed/kUJmAcSf',
        'md5': '706956a6c875873d51010921310e4bc6',
        'info_dict': {
            'id': 'kUJmAcSf',
            'ext': 'mp4',
            'title': 'VideoPress Demo',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 634.6,
            'timestamp': 1434983935,
            'upload_date': '20150622',
            'age_limit': 0,
        },
    }, {
        # 17+, requires birth_* params
        'url': 'https://videopress.com/embed/iH3gstfZ',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return re.findall(
            r'<iframe[^>]+src=["\']((?:https?://)?videopress\.com/embed/[\da-zA-Z]+)',
            webpage)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        query = random_birthday('birth_year', 'birth_month', 'birth_day')
        video = self._download_json(
            'https://public-api.wordpress.com/rest/v1.1/videos/%s' % video_id,
            video_id, query=query)

        title = video['title']

        def base_url(scheme):
            return try_get(
                video, lambda x: x['file_url_base'][scheme], compat_str)

        base_url = base_url('https') or base_url('http')

        QUALITIES = ('std', 'dvd', 'hd')
        quality = qualities(QUALITIES)

        formats = []
        for format_id, f in video['files'].items():
            if not isinstance(f, dict):
                continue
            for ext, path in f.items():
                if ext in ('mp4', 'ogg'):
                    formats.append({
                        'url': urljoin(base_url, path),
                        'format_id': '%s-%s' % (format_id, ext),
                        'ext': determine_ext(path, ext),
                        'quality': quality(format_id),
                    })
        original_url = try_get(video, lambda x: x['original'], compat_str)
        if original_url:
            formats.append({
                'url': original_url,
                'format_id': 'original',
                'quality': len(QUALITIES),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': video.get('description'),
            'thumbnail': video.get('poster'),
            'duration': float_or_none(video.get('duration'), 1000),
            'timestamp': unified_timestamp(video.get('upload_date')),
            'age_limit': parse_age_limit(video.get('rating')),
            'formats': formats,
        }
