# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    sanitized_Request,
)


class SportDeutschlandIE(InfoExtractor):
    _VALID_URL = r'https?://sportdeutschland\.tv/(?P<sport>[^/?#]+)/(?P<id>[^?#/]+)(?:$|[?#])'
    _TESTS = [{
        'url': 'https://sportdeutschland.tv/badminton/re-live-deutsche-meisterschaften-2020-halbfinals?playlistId=0',
        'info_dict': {
            'id': 're-live-deutsche-meisterschaften-2020-halbfinals',
            'ext': 'mp4',
            'title': 're:Re-live: Deutsche Meisterschaften 2020.*Halbfinals',
            'categories': ['Badminton-Deutschland'],
            'view_count': int,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
            'timestamp': int,
            'upload_date': '20200201',
            'description': 're:.*',  # meaningless description for THIS video
        },
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        sport_id = mobj.group('sport')

        api_url = 'https://proxy.vidibusdynamic.net/ssl/backend.sportdeutschland.tv/api/permalinks/%s/%s?access_token=true' % (
            sport_id, video_id)
        req = sanitized_Request(api_url, headers={
            'Accept': 'application/vnd.vidibus.v2.html+json',
            'Referer': url,
        })
        data = self._download_json(req, video_id)

        asset = data['asset']
        categories = [data['section']['title']]

        formats = []
        smil_url = asset['video']
        if '.smil' in smil_url:
            m3u8_url = smil_url.replace('.smil', '.m3u8')
            formats.extend(
                self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4'))

            smil_doc = self._download_xml(
                smil_url, video_id, note='Downloading SMIL metadata')
            base_url_el = smil_doc.find('./head/meta')
            if base_url_el:
                base_url = base_url_el.attrib['base']
            formats.extend([{
                'format_id': 'rmtp',
                'url': base_url if base_url_el else n.attrib['src'],
                'play_path': n.attrib['src'],
                'ext': 'flv',
                'preference': -100,
                'format_note': 'Seems to fail at example stream',
            } for n in smil_doc.findall('./body/video')])
        else:
            formats.append({'url': smil_url})

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': asset['title'],
            'thumbnail': asset.get('image'),
            'description': asset.get('teaser'),
            'duration': asset.get('duration'),
            'categories': categories,
            'view_count': asset.get('views'),
            'rtmp_live': asset.get('live'),
            'timestamp': parse_iso8601(asset.get('date')),
        }
