# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import unified_strdate


class CozyTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cozy\.tv/(?P<uploader>[^/]+)/replays/(?P<id>[^/$#&?]+)'

    _TESTS = [{
        'url': 'https://cozy.tv/beardson/replays/2021-11-19_1',
        'info_dict': {
            'id': 'beardson-2021-11-19_1',
            'ext': 'mp4',
            'title': 'pokemon pt2',
            'uploader': 'beardson',
            'upload_date': '20211119',
            'was_live': True,
            'duration': 7981,
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        uploader, date = self._match_valid_url(url).groups()
        id = f'{uploader}-{date}'
        data_json = self._download_json(f'https://api.cozy.tv/cache/{uploader}/replay/{date}', id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://cozycdn.foxtrotstream.xyz/replays/{uploader}/{date}/index.m3u8', id, ext='mp4')
        return {
            'id': id,
            'title': data_json.get('title'),
            'uploader': data_json.get('user') or uploader,
            'upload_date': unified_strdate(data_json.get('date')),
            'was_live': True,
            'duration': data_json.get('duration'),
            'formats': formats,
            'subtitles': subtitles,
        }
