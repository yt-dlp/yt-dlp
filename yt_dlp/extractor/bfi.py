# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import extract_attributes


class BFIPlayerIE(InfoExtractor):
    IE_NAME = 'bfi:player'
    _VALID_URL = r'https?://player\.bfi\.org\.uk/[^/]+/film/watch-(?P<id>[\w-]+)-online'
    _TEST = {
        'url': 'https://player.bfi.org.uk/free/film/watch-computer-doctor-1974-online',
        'md5': 'e8783ebd8e061ec4bc6e9501ed547de8',
        'info_dict': {
            'id': 'htNnhlZjE60C9VySkQEIBtU-cNV1Xx63',
            'ext': 'mp4',
            'title': 'Computer Doctor',
            'description': 'md5:fb6c240d40c4dbe40428bdd62f78203b',
        },
        'skip': 'BFI Player films cannot be played outside of the UK',
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        entries = []
        for player_el in re.findall(r'(?s)<[^>]+class="player"[^>]*>', webpage):
            player_attr = extract_attributes(player_el)
            ooyala_id = player_attr.get('data-video-id')
            if not ooyala_id:
                continue
            entries.append(self.url_result(
                'ooyala:' + ooyala_id, 'Ooyala',
                ooyala_id, player_attr.get('data-label')))
        return self.playlist_result(entries)
