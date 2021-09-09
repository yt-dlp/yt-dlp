# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import unified_strdate


class OlympicsReplayIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?olympics\.com/tokyo-2020/(?:[a-z]{2}/)?replay/(?P<id>[^/#&?]+)'
    _TESTS = [{
        'url': 'https://olympics.com/tokyo-2020/en/replay/300622eb-abc0-43ea-b03b-c5f2d429ec7b/jumping-team-qualifier',
        'info_dict': {
            'id': '300622eb-abc0-43ea-b03b-c5f2d429ec7b',
            'ext': 'mp4',
            'title': 'Jumping Team Qualifier',
            'release_date': '20210806',
            'upload_date': '20210713',
        },
        'params': {
            'format': 'bv',
        },
    }, {
        'url': 'https://olympics.com/tokyo-2020/en/replay/bd242924-4b22-49a5-a846-f1d4c809250d/mens-bronze-medal-match-hun-esp',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        # The parameters are hardcoded in the webpage, it's not necessary to download the webpage just for these parameters.
        # If in downloading webpage serves other functions aswell, then extract these parameters from it.
        token_url = 'https://appovptok.ovpobs.tv/api/identity/app/token?api_key=OTk5NDcxOjpvY3N3LWFwaXVzZXI%3D&api_secret=ODY4ODM2MjE3ODMwYmVjNTAxMWZlMDJiMTYxZmY0MjFiMjMwMjllMjJmNDA1YWRiYzA5ODcxYTZjZTljZDkxOTo6NTM2NWIzNjRlMTM1ZmI2YWNjNmYzMGMzOGM3NzZhZTY%3D'
        token = self._download_webpage(token_url, id)
        headers = {'x-obs-app-token': token}
        data_json = self._download_json(f'https://appocswtok.ovpobs.tv/api/schedule-sessions/{id}?include=stream',
                                        id, headers=headers)
        meta_data = data_json['data']['attributes']
        for t_dict in data_json['included']:
            if t_dict.get('type') == 'Stream':
                stream_data = t_dict['attributes']
        m3u8_url = self._download_json(
            'https://meteringtok.ovpobs.tv/api/playback-sessions', id, headers=headers, query={
                'alias': stream_data['alias'],
                'stream': stream_data['stream'],
                'type': 'vod'
            })['data']['attributes']['url']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, id)
        self._sort_formats(formats)

        return {
            'id': id,
            'title': meta_data['title'],
            'release_date': unified_strdate(meta_data.get('start') or meta_data.get('broadcastPublished')),
            'upload_date': unified_strdate(meta_data.get('publishedAt')),
            'formats': formats,
            'subtitles': subtitles,
        }
