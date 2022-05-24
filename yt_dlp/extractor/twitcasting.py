import itertools
import re

from .common import InfoExtractor
from ..dependencies import websockets
from ..utils import (
    clean_html,
    ExtractorError,
    float_or_none,
    get_element_by_class,
    get_element_by_id,
    parse_duration,
    qualities,
    str_to_int,
    traverse_obj,
    try_get,
    unified_timestamp,
    urlencode_postdata,
    urljoin,
)


class TwitCastingIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?twitcasting\.tv/(?P<uploader_id>[^/]+)/(?:movie|twplayer)/(?P<id>\d+)'
    _M3U8_HEADERS = {
        'Origin': 'https://twitcasting.tv',
        'Referer': 'https://twitcasting.tv/',
    }
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
    }, {
        'note': 'archive is split in 2 parts',
        'url': 'https://twitcasting.tv/loft_heaven/movie/685979292',
        'info_dict': {
            'id': '685979292',
            'ext': 'mp4',
            'title': '南波一海のhear_here “ナタリー望月哲さんに聞く編集と「渋谷系狂騒曲」”',
            'duration': 6964.599334,
        },
        'playlist_mincount': 2,
    }]

    def _real_extract(self, url):
        uploader_id, video_id = self._match_valid_url(url).groups()

        video_password = self.get_param('videopassword')
        request_data = None
        if video_password:
            request_data = urlencode_postdata({
                'password': video_password,
            }, encoding='utf-8')
        webpage, urlh = self._download_webpage_handle(
            url, video_id, data=request_data,
            headers={'Origin': 'https://twitcasting.tv'})
        if urlh.geturl() != url and request_data:
            webpage = self._download_webpage(
                urlh.geturl(), video_id, data=request_data,
                headers={'Origin': 'https://twitcasting.tv'},
                note='Retrying authentication')
        # has to check here as the first request can contain password input form even if the password is correct
        if re.search(r'<form\s+method="POST">\s*<input\s+[^>]+?name="password"', webpage):
            raise ExtractorError('This video is protected by a password, use the --video-password option', expected=True)

        title = (clean_html(get_element_by_id('movietitle', webpage))
                 or self._html_search_meta(['og:title', 'twitter:title'], webpage, fatal=True))

        video_js_data = try_get(
            webpage,
            lambda x: self._parse_json(self._search_regex(
                r'data-movie-playlist=\'([^\']+?)\'',
                x, 'movie playlist', default=None), video_id)['2'], list)

        thumbnail = traverse_obj(video_js_data, (0, 'thumbnailUrl')) or self._og_search_thumbnail(webpage)
        description = clean_html(get_element_by_id(
            'authorcomment', webpage)) or self._html_search_meta(
            ['description', 'og:description', 'twitter:description'], webpage)
        duration = (try_get(video_js_data, lambda x: sum(float_or_none(y.get('duration')) for y in x) / 1000)
                    or parse_duration(clean_html(get_element_by_class('tw-player-duration-time', webpage))))
        view_count = str_to_int(self._search_regex(
            (r'Total\s*:\s*([\d,]+)\s*Views', r'総視聴者\s*:\s*([\d,]+)\s*</'), webpage, 'views', None))
        timestamp = unified_timestamp(self._search_regex(
            r'data-toggle="true"[^>]+datetime="([^"]+)"',
            webpage, 'datetime', None))

        stream_server_data = self._download_json(
            'https://twitcasting.tv/streamserver.php?target=%s&mode=client' % uploader_id, video_id,
            'Downloading live info', fatal=False)

        is_live = 'data-status="online"' in webpage
        if not traverse_obj(stream_server_data, 'llfmp4') and is_live:
            self.raise_login_required(method='cookies')

        base_dict = {
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'duration': duration,
            'view_count': view_count,
            'is_live': is_live,
        }

        def find_dmu(x):
            data_movie_url = self._search_regex(
                r'data-movie-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
                x, 'm3u8 url', group='url', default=None)
            if data_movie_url:
                return [data_movie_url]

        m3u8_urls = (try_get(webpage, find_dmu, list)
                     or traverse_obj(video_js_data, (..., 'source', 'url'))
                     or ([f'https://twitcasting.tv/{uploader_id}/metastream.m3u8'] if is_live else None))
        if not m3u8_urls:
            raise ExtractorError('Failed to get m3u8 playlist')

        if is_live:
            m3u8_url = m3u8_urls[0]
            formats = self._extract_m3u8_formats(
                m3u8_url, video_id, ext='mp4', m3u8_id='hls',
                live=True, headers=self._M3U8_HEADERS)

            if traverse_obj(stream_server_data, ('hls', 'source')):
                formats.extend(self._extract_m3u8_formats(
                    m3u8_url, video_id, ext='mp4', m3u8_id='source',
                    live=True, query={'mode': 'source'},
                    note='Downloading source quality m3u8',
                    headers=self._M3U8_HEADERS, fatal=False))

            if websockets:
                qq = qualities(['base', 'mobilesource', 'main'])
                streams = traverse_obj(stream_server_data, ('llfmp4', 'streams')) or {}
                for mode, ws_url in streams.items():
                    formats.append({
                        'url': ws_url,
                        'format_id': 'ws-%s' % mode,
                        'ext': 'mp4',
                        'quality': qq(mode),
                        'source_preference': -10,
                        # TwitCasting simply sends moof atom directly over WS
                        'protocol': 'websocket_frag',
                    })

            self._sort_formats(formats, ('source',))

            infodict = {
                'formats': formats
            }
        elif len(m3u8_urls) == 1:
            formats = self._extract_m3u8_formats(
                m3u8_urls[0], video_id, 'mp4', headers=self._M3U8_HEADERS)
            self._sort_formats(formats)
            infodict = {
                # No problem here since there's only one manifest
                'formats': formats,
                'http_headers': self._M3U8_HEADERS,
            }
        else:
            infodict = {
                '_type': 'multi_video',
                'entries': [{
                    'id': f'{video_id}-{num}',
                    'url': m3u8_url,
                    'ext': 'mp4',
                    # Requesting the manifests here will cause download to fail.
                    # So use ffmpeg instead. See: https://github.com/yt-dlp/yt-dlp/issues/382
                    'protocol': 'm3u8',
                    'http_headers': self._M3U8_HEADERS,
                    **base_dict,
                } for (num, m3u8_url) in enumerate(m3u8_urls)],
            }

        return {
            'id': video_id,
            **base_dict,
            **infodict,
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
            # fetch unfiltered /show to find running livestreams; we can't get ID of the password-protected livestream above
            webpage = self._download_webpage(
                f'https://twitcasting.tv/{uploader_id}/show/', uploader_id,
                note='Downloading live history')
            is_live = self._search_regex(r'(?s)(<span\s*class="tw-movie-thumbnail-badge"\s*data-status="live">\s*LIVE)', webpage, 'is live?', default=None)
            if is_live:
                # get the first live; running live is always at the first
                current_live = self._search_regex(
                    r'(?s)<a\s+class="tw-movie-thumbnail"\s*href="/[^/]+/movie/(?P<video_id>\d+)"\s*>.+?</a>',
                    webpage, 'current live ID 2', default=None, group='video_id')
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
