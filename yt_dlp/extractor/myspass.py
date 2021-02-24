# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    parse_duration,
    xpath_text,
)


class MySpassIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?myspass\.de/([^/]+/)*(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.myspass.de/myspass/shows/tvshows/absolute-mehrheit/Absolute-Mehrheit-vom-17022013-Die-Highlights-Teil-2--/11741/',
        'md5': '0b49f4844a068f8b33f4b7c88405862b',
        'info_dict': {
            'id': '11741',
            'ext': 'mp4',
            'description': 'Wer kann in die Fußstapfen von Wolfgang Kubicki treten und die Mehrheit der Zuschauer hinter sich versammeln? Wird vielleicht sogar die Absolute Mehrheit geknackt und der Jackpot von 200.000 Euro mit nach Hause genommen?',
            'title': '17.02.2013 - Die Highlights, Teil 2',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        metadata = self._download_xml(
            'http://www.myspass.de/myspass/includes/apps/video/getvideometadataxml.php?id=' + video_id,
            video_id)

        title = xpath_text(metadata, 'title', fatal=True)
        video_url = xpath_text(metadata, 'url_flv', 'download url', True)
        video_id_int = int(video_id)
        for group in re.search(r'/myspass2009/\d+/(\d+)/(\d+)/(\d+)/', video_url).groups():
            group_int = int(group)
            if group_int > video_id_int:
                video_url = video_url.replace(
                    group, compat_str(group_int // video_id_int))

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'thumbnail': xpath_text(metadata, 'imagePreview'),
            'description': xpath_text(metadata, 'description'),
            'duration': parse_duration(xpath_text(metadata, 'duration')),
            'series': xpath_text(metadata, 'format'),
            'season_number': int_or_none(xpath_text(metadata, 'season')),
            'season_id': xpath_text(metadata, 'season_id'),
            'episode': title,
            'episode_number': int_or_none(xpath_text(metadata, 'episode')),
        }
