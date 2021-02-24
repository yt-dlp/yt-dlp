# coding: utf-8
from __future__ import unicode_literals

import hashlib
import time

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    sanitized_Request,
)


def _get_api_key(api_path):
    if api_path.endswith('?'):
        api_path = api_path[:-1]

    api_key = 'fb5f58a820353bd7095de526253c14fd'
    a = '{0:}{1:}{2:}'.format(api_key, api_path, int(round(time.time() / 24 / 3600)))
    return hashlib.md5(a.encode('ascii')).hexdigest()


class StreamCZIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?stream\.cz/.+/(?P<id>[0-9]+)'
    _API_URL = 'http://www.stream.cz/API'

    _TESTS = [{
        'url': 'http://www.stream.cz/peklonataliri/765767-ecka-pro-deti',
        'md5': '934bb6a6d220d99c010783c9719960d5',
        'info_dict': {
            'id': '765767',
            'ext': 'mp4',
            'title': 'Peklo na talíři: Éčka pro děti',
            'description': 'Taška s grónskou pomazánkou a další pekelnosti ZDE',
            'thumbnail': 're:^http://im.stream.cz/episode/52961d7e19d423f8f06f0100',
            'duration': 256,
        },
    }, {
        'url': 'http://www.stream.cz/blanik/10002447-tri-roky-pro-mazanka',
        'md5': '849a88c1e1ca47d41403c2ba5e59e261',
        'info_dict': {
            'id': '10002447',
            'ext': 'mp4',
            'title': 'Kancelář Blaník: Tři roky pro Mazánka',
            'description': 'md5:3862a00ba7bf0b3e44806b544032c859',
            'thumbnail': 're:^http://im.stream.cz/episode/537f838c50c11f8d21320000',
            'duration': 368,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_path = '/episode/%s' % video_id

        req = sanitized_Request(self._API_URL + api_path)
        req.add_header('Api-Password', _get_api_key(api_path))
        data = self._download_json(req, video_id)

        formats = []
        for quality, video in enumerate(data['video_qualities']):
            for f in video['formats']:
                typ = f['type'].partition('/')[2]
                qlabel = video.get('quality_label')
                formats.append({
                    'format_note': '%s-%s' % (qlabel, typ) if qlabel else typ,
                    'format_id': '%s-%s' % (typ, f['quality']),
                    'url': f['source'],
                    'height': int_or_none(f['quality'].rstrip('p')),
                    'quality': quality,
                })
        self._sort_formats(formats)

        image = data.get('image')
        if image:
            thumbnail = self._proto_relative_url(
                image.replace('{width}', '1240').replace('{height}', '697'),
                scheme='http:',
            )
        else:
            thumbnail = None

        stream = data.get('_embedded', {}).get('stream:show', {}).get('name')
        if stream:
            title = '%s: %s' % (stream, data['name'])
        else:
            title = data['name']

        subtitles = {}
        srt_url = data.get('subtitles_srt')
        if srt_url:
            subtitles['cs'] = [{
                'ext': 'srt',
                'url': srt_url,
            }]

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
            'description': data.get('web_site_text'),
            'duration': int_or_none(data.get('duration')),
            'view_count': int_or_none(data.get('views')),
            'subtitles': subtitles,
        }
