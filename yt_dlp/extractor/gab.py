# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    str_to_int,
)


class GabTVIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)tv.gab.com/channel/[^/]+/view/(?P<id>[a-z0-9-]+)'
    _TESTS = [{
        'url': 'https://tv.gab.com/channel/wurzelroot/view/why-was-america-in-afghanistan-61217eacea5665de450d0488',
        'info_dict': {
            'id': '61217eacea5665de450d0488',
            'ext': 'mp4',
            'title': 'WHY WAS AMERICA IN AFGHANISTAN - AMERICA FIRST AGAINST AMERICAN OLIGARCHY',
            'description': None,
            'uploader': 'Wurzelroot',
            'uploader_id': '608fb0a85738fd1974984f7d',
            'thumbnail': 'https://tv.gab.com/image/61217eacea5665de450d0488',
        }
    }]

    def _real_extract(self, url):
        id = self._match_id(url).split('-')[-1]
        webpage = self._download_webpage(url, id)
        channel_id = self._search_regex(r'data-channel-id=\"(?P<channel_id>[^\"]+)', webpage, 'channel_id')
        channel_name = self._search_regex(r'data-channel-name=\"(?P<channel_id>[^\"]+)', webpage, 'channel_name')
        title = self._search_regex(r'data-episode-title=\"(?P<channel_id>[^\"]+)', webpage, 'title')
        view_key = self._search_regex(r'data-view-key=\"(?P<channel_id>[^\"]+)', webpage, 'view_key')
        description = clean_html(self._html_search_regex(self._meta_regex('description'), webpage, 'description', group='content')) or None
        available_resolutions = re.findall(r'<a\ data-episode-id=\"%s\"\ data-resolution=\"(?P<resolution>[^\"]+)' % id, webpage)

        formats = []
        for resolution in available_resolutions:
            frmt = {
                'url': f'https://tv.gab.com/media/{id}?viewKey={view_key}&r={resolution}',
                'format_id': resolution,
                'vcodec': 'h264',
                'acodec': 'aac',
                'ext': 'mp4'
            }
            if 'audio-' in resolution:
                frmt['abr'] = str_to_int(resolution.replace('audio-', ''))
                frmt['height'] = 144
                frmt['quality'] = -10
            else:
                frmt['height'] = str_to_int(resolution.replace('p', ''))
            formats.append(frmt)
        self._sort_formats(formats)

        return {
            'id': id,
            'title': title,
            'formats': formats,
            'description': description,
            'uploader': channel_name,
            'uploader_id': channel_id,
            'thumbnail': f'https://tv.gab.com/image/{id}',
        }
