# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import js_to_json


class LineTVIE(InfoExtractor):
    _VALID_URL = r'https?://tv\.line\.me/v/(?P<id>\d+)_[^/]+-(?P<segment>ep\d+-\d+)'

    _TESTS = [{
        'url': 'https://tv.line.me/v/793123_goodbye-mrblack-ep1-1/list/69246',
        'info_dict': {
            'id': '793123_ep1-1',
            'ext': 'mp4',
            'title': 'Goodbye Mr.Black | EP.1-1',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 998.509,
            'view_count': int,
        },
    }, {
        'url': 'https://tv.line.me/v/2587507_%E6%B4%BE%E9%81%A3%E5%A5%B3%E9%86%ABx-ep1-02/list/185245',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        series_id, segment = re.match(self._VALID_URL, url).groups()
        video_id = '%s_%s' % (series_id, segment)

        webpage = self._download_webpage(url, video_id)

        player_params = self._parse_json(self._search_regex(
            r'naver\.WebPlayer\(({[^}]+})\)', webpage, 'player parameters'),
            video_id, transform_source=js_to_json)

        video_info = self._download_json(
            'https://global-nvapis.line.me/linetv/rmcnmv/vod_play_videoInfo.json',
            video_id, query={
                'videoId': player_params['videoId'],
                'key': player_params['key'],
            })

        stream = video_info['streams'][0]
        extra_query = '?__gda__=' + stream['key']['value']
        formats = self._extract_m3u8_formats(
            stream['source'] + extra_query, video_id, ext='mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')

        for a_format in formats:
            a_format['url'] += extra_query

        duration = None
        for video in video_info.get('videos', {}).get('list', []):
            encoding_option = video.get('encodingOption', {})
            abr = video['bitrate']['audio']
            vbr = video['bitrate']['video']
            tbr = abr + vbr
            formats.append({
                'url': video['source'],
                'format_id': 'http-%d' % int(tbr),
                'height': encoding_option.get('height'),
                'width': encoding_option.get('width'),
                'abr': abr,
                'vbr': vbr,
                'filesize': video.get('size'),
            })
            if video.get('duration') and duration is None:
                duration = video['duration']

        self._sort_formats(formats)

        if not formats[0].get('width'):
            formats[0]['vcodec'] = 'none'

        title = self._og_search_title(webpage)

        # like_count requires an additional API request https://tv.line.me/api/likeit/getCount

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'extra_param_to_segment_url': extra_query[1:],
            'duration': duration,
            'thumbnails': [{'url': thumbnail['source']}
                           for thumbnail in video_info.get('thumbnails', {}).get('list', [])],
            'view_count': video_info.get('meta', {}).get('count'),
        }
