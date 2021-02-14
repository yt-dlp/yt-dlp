# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    js_to_json,
)


class RTPIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rtp\.pt/play/p(?P<program_id>[0-9]+)/(?P<id>[^/?#]+)/?'
    _TESTS = [{
        'url': 'http://www.rtp.pt/play/p405/e174042/paixoes-cruzadas',
        'md5': 'e736ce0c665e459ddb818546220b4ef8',
        'info_dict': {
            'id': 'e174042',
            'ext': 'mp3',
            'title': 'Paixões Cruzadas',
            'description': 'As paixões musicais de António Cartaxo e António Macedo',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'http://www.rtp.pt/play/p831/a-quimica-das-coisas',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        title = self._html_search_meta(
            'twitter:title', webpage, display_name='title', fatal=True)

        config = self._parse_json(self._search_regex(
            r'(?s)RTPPlayer\(({.+?})\);', webpage,
            'player config'), video_id, js_to_json)
        file_url = config['file']
        ext = determine_ext(file_url)
        if ext == 'm3u8':
            file_key = config.get('fileKey')
            formats = self._extract_m3u8_formats(
                file_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=file_key)
            if file_key:
                formats.append({
                    'url': 'https://cdn-ondemand.rtp.pt' + file_key,
                    'preference': 1,
                })
            self._sort_formats(formats)
        else:
            formats = [{
                'url': file_url,
                'ext': ext,
            }]
        if config.get('mediaType') == 'audio':
            for f in formats:
                f['vcodec'] = 'none'

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': self._html_search_meta(['description', 'twitter:description'], webpage),
            'thumbnail': config.get('poster') or self._og_search_thumbnail(webpage),
        }
