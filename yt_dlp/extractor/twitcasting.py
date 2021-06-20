# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..downloader.websocket import has_websockets
from ..utils import (
    clean_html,
    float_or_none,
    get_element_by_class,
    get_element_by_id,
    parse_duration,
    qualities,
    str_to_int,
    try_get,
    unified_timestamp,
    urlencode_postdata,
    urljoin,
    ExtractorError,
)


class TwitCastingIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?twitcasting\.tv/(?P<uploader_id>[^/]+)/(?:movie|twplayer)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://twitcasting.tv/ivetesangalo/movie/2357609',
        'md5': '745243cad58c4681dc752490f7540d7f',
        'info_dict': {
            'id': '2357609',
            'ext': 'mp4',
            'title': 'Live #2357609',
            'uploader_id': 'ivetesangalo',
            'description': 'Twitter Oficial da cantora brasileira Ivete Sangalo.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20110822',
            'timestamp': 1314010824,
            'duration': 32,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://twitcasting.tv/mttbernardini/movie/3689740',
        'info_dict': {
            'id': '3689740',
            'ext': 'mp4',
            'title': 'Live playing something #3689740',
            'uploader_id': 'mttbernardini',
            'description': 'Salve, io sono Matto (ma con la e). Questa è la mia presentazione, in quanto sono letteralmente matto (nel senso di strano), con qualcosa in più.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20120212',
            'timestamp': 1329028024,
            'duration': 681,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
            'videopassword': 'abc',
        },
    }]

    def _real_extract(self, url):
        uploader_id, video_id = re.match(self._VALID_URL, url).groups()

        video_password = self.get_param('videopassword')
        request_data = None
        if video_password:
            request_data = urlencode_postdata({
                'password': video_password,
            })
        webpage = self._download_webpage(
            url, video_id, data=request_data,
            headers={'Origin': 'https://twitcasting.tv'})

        title = (clean_html(get_element_by_id('movietitle', webpage))
                 or self._html_search_meta(['og:title', 'twitter:title'], webpage, fatal=True))

        video_js_data = {}
        m3u8_url = self._search_regex(
            r'data-movie-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
            webpage, 'm3u8 url', group='url', default=None)
        if not m3u8_url:
            video_js_data = self._parse_json(self._search_regex(
                r'data-movie-playlist=(["\'])(?P<url>(?:(?!\1).)+)',
                webpage, 'movie playlist', group='url', default='[{}]'), video_id)
            if isinstance(video_js_data, dict):
                video_js_data = list(video_js_data.values())[0]
            video_js_data = video_js_data[0]
            m3u8_url = try_get(video_js_data, lambda x: x['source']['url'])

        stream_server_data = self._download_json(
            'https://twitcasting.tv/streamserver.php?target=%s&mode=client' % uploader_id, video_id,
            'Downloading live info', fatal=False)

        is_live = 'data-status="online"' in webpage
        formats = []
        if is_live and not m3u8_url:
            m3u8_url = 'https://twitcasting.tv/%s/metastream.m3u8' % uploader_id
        if is_live and has_websockets and stream_server_data:
            qq = qualities(['base', 'mobilesource', 'main'])
            for mode, ws_url in stream_server_data['llfmp4']['streams'].items():
                formats.append({
                    'url': ws_url,
                    'format_id': 'ws-%s' % mode,
                    'ext': 'mp4',
                    'quality': qq(mode),
                    'protocol': 'websocket_frag',  # TwitCasting simply sends moof atom directly over WS
                })

        thumbnail = video_js_data.get('thumbnailUrl') or self._og_search_thumbnail(webpage)
        description = clean_html(get_element_by_id(
            'authorcomment', webpage)) or self._html_search_meta(
            ['description', 'og:description', 'twitter:description'], webpage)
        duration = float_or_none(video_js_data.get(
            'duration'), 1000) or parse_duration(clean_html(
                get_element_by_class('tw-player-duration-time', webpage)))
        view_count = str_to_int(self._search_regex(
            r'Total\s*:\s*([\d,]+)\s*Views', webpage, 'views', None))
        timestamp = unified_timestamp(self._search_regex(
            r'data-toggle="true"[^>]+datetime="([^"]+)"',
            webpage, 'datetime', None))

        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', live=is_live))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
            'is_live': is_live,
        }


class TwitCastingLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?twitcasting\.tv/(?P<id>[^/]+)/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://twitcasting.tv/ivetesangalo',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        uploader_id = self._match_id(url)
        self.to_screen(
            'Downloading live video of user {0}. '
            'Pass "https://twitcasting.tv/{0}/show" to download the history'.format(uploader_id))

        webpage = self._download_webpage(url, uploader_id)
        current_live = self._search_regex(
            (r'data-type="movie" data-id="(\d+)">',
             r'tw-sound-flag-open-link" data-id="(\d+)" style=',),
            webpage, 'current live ID', default=None)
        if not current_live:
            raise ExtractorError('The user is not currently live')
        return self.url_result('https://twitcasting.tv/%s/movie/%s' % (uploader_id, current_live))


class TwitCastingUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?twitcasting\.tv/(?P<id>[^/]+)/show/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://twitcasting.tv/noriyukicas/show',
        'only_matching': True,
    }]

    def _entries(self, uploader_id):
        base_url = next_url = 'https://twitcasting.tv/%s/show' % uploader_id
        for page_num in itertools.count(1):
            webpage = self._download_webpage(
                next_url, uploader_id, query={'filter': 'watchable'}, note='Downloading page %d' % page_num)
            matches = re.finditer(
                r'''(?isx)<a\s+class="tw-movie-thumbnail"\s*href="(?P<url>/[^/]+/movie/\d+)"\s*>.+?</a>''',
                webpage)
            for mobj in matches:
                yield self.url_result(urljoin(base_url, mobj.group('url')))

            next_url = self._search_regex(
                r'<a href="(/%s/show/%d-\d+)[?"]' % (re.escape(uploader_id), page_num),
                webpage, 'next url', default=None)
            next_url = urljoin(base_url, next_url)
            if not next_url:
                return

    def _real_extract(self, url):
        uploader_id = self._match_id(url)
        return self.playlist_result(
            self._entries(uploader_id), uploader_id, '%s - Live History' % uploader_id)
