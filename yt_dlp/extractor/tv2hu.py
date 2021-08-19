# encoding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import int_or_none


class TV2HuIE(InfoExtractor):
    IE_NAME = 'tv2.hu'
    _VALID_URL = r'https?://(?:www\.)?tv2\.hu/(?:[^/]+/)+(?P<id>\d+)_[^/?#]+?\.html'
    _TESTS = [{
        'url': 'http://tv2.hu/ezek_megorultek/217679_ezek-megorultek---1.-adas-1.-resz.html',
        'md5': '585e58e2e090f34603804bb2c48e98d8',
        'info_dict': {
            'id': '217679',
            'ext': 'mp4',
            'title': 'Ezek megőrültek! - 1. adás 1. rész',
            'upload_date': '20160826',
            'thumbnail': r're:^https?://.*\.jpg$'
        }
    }, {
        'url': 'http://tv2.hu/ezek_megorultek/teljes_adasok/217677_ezek-megorultek---1.-adas-2.-resz.html',
        'only_matching': True
    }, {
        'url': 'http://tv2.hu/musoraink/aktiv/aktiv_teljes_adas/217963_aktiv-teljes-adas---2016.08.30..html',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_url = self._search_regex(
            r'jsonUrl\s*=\s*"([^"]+)"', webpage, 'json url')
        json_data = self._download_json(json_url, video_id)

        formats = []
        for b in ('bitrates', 'backupBitrates'):
            bitrates = json_data.get(b, {})
            m3u8_url = bitrates.get('hls')
            if m3u8_url:
                formats.extend(self._extract_wowza_formats(
                    m3u8_url, video_id, skip_protocols=['rtmp', 'rtsp']))

            for mp4_url in bitrates.get('mp4', []):
                height = int_or_none(self._search_regex(
                    r'\.(\d+)p\.mp4', mp4_url, 'height', default=None))
                formats.append({
                    'format_id': 'http' + ('-%d' % height if height else ''),
                    'url': mp4_url,
                    'height': height,
                    'width': int_or_none(height / 9.0 * 16.0 if height else None),
                })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage).strip(),
            'thumbnail': self._og_search_thumbnail(webpage),
            'upload_date': self._search_regex(
                r'/vod/(\d{8})/', json_url, 'upload_date', default=None),
            'formats': formats,
        }
