import re

from .common import InfoExtractor
from ..compat import compat_parse_qs
from ..dependencies import websockets
from ..utils import (
    ExtractorError,
    WebSocketsWrapper,
    js_to_json,
    sanitized_Request,
    traverse_obj,
    update_url_query,
    urlencode_postdata,
    urljoin,
)


class FC2IE(InfoExtractor):
    _VALID_URL = r'^(?:https?://video\.fc2\.com/(?:[^/]+/)*content/|fc2:)(?P<id>[^/]+)'
    IE_NAME = 'fc2'
    _NETRC_MACHINE = 'fc2'
    _TESTS = [{
        'url': 'http://video.fc2.com/en/content/20121103kUan1KHs',
        'md5': 'a6ebe8ebe0396518689d963774a54eb7',
        'info_dict': {
            'id': '20121103kUan1KHs',
            'ext': 'flv',
            'title': 'Boxing again with Puff',
        },
    }, {
        'url': 'http://video.fc2.com/en/content/20150125cEva0hDn/',
        'info_dict': {
            'id': '20150125cEva0hDn',
            'ext': 'mp4',
        },
        'params': {
            'username': 'ytdl@yt-dl.org',
            'password': '(snip)',
        },
        'skip': 'requires actual password',
    }, {
        'url': 'http://video.fc2.com/en/a/content/20130926eZpARwsF',
        'only_matching': True,
    }]

    def _login(self):
        username, password = self._get_login_info()
        if username is None or password is None:
            return False

        # Log in
        login_form_strs = {
            'email': username,
            'password': password,
            'done': 'video',
            'Submit': ' Login ',
        }

        login_data = urlencode_postdata(login_form_strs)
        request = sanitized_Request(
            'https://secure.id.fc2.com/index.php?mode=login&switch_language=en', login_data)

        login_results = self._download_webpage(request, None, note='Logging in', errnote='Unable to log in')
        if 'mode=redirect&login=done' not in login_results:
            self.report_warning('unable to log in: bad username or password')
            return False

        # this is also needed
        login_redir = sanitized_Request('http://id.fc2.com/?mode=redirect&login=done')
        self._download_webpage(
            login_redir, None, note='Login redirect', errnote='Login redirect failed')

        return True

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._login()
        webpage = None
        if not url.startswith('fc2:'):
            webpage = self._download_webpage(url, video_id)
            self.cookiejar.clear_session_cookies()  # must clear
            self._login()

        title, thumbnail, description = None, None, None
        if webpage is not None:
            title = self._html_search_regex(
                (r'<h2\s+class="videoCnt_title">([^<]+?)</h2>',
                 r'\s+href="[^"]+"\s*title="([^"]+?)"\s*rel="nofollow">\s*<img',
                 # there's two matches in the webpage
                 r'\s+href="[^"]+"\s*title="([^"]+?)"\s*rel="nofollow">\s*\1'),
                webpage,
                'title', fatal=False)
            thumbnail = self._og_search_thumbnail(webpage)
            description = self._og_search_description(webpage, default=None)

        vidplaylist = self._download_json(
            'https://video.fc2.com/api/v3/videoplaylist/%s?sh=1&fs=0' % video_id, video_id,
            note='Downloading info page')
        vid_url = traverse_obj(vidplaylist, ('playlist', 'nq'))
        if not vid_url:
            raise ExtractorError('Unable to extract video URL')
        vid_url = urljoin('https://video.fc2.com/', vid_url)

        return {
            'id': video_id,
            'title': title,
            'url': vid_url,
            'ext': 'mp4',
            'protocol': 'm3u8_native',
            'description': description,
            'thumbnail': thumbnail,
        }


class FC2EmbedIE(InfoExtractor):
    _VALID_URL = r'https?://video\.fc2\.com/flv2\.swf\?(?P<query>.+)'
    IE_NAME = 'fc2:embed'

    _TEST = {
        'url': 'http://video.fc2.com/flv2.swf?t=201404182936758512407645&i=20130316kwishtfitaknmcgd76kjd864hso93htfjcnaogz629mcgfs6rbfk0hsycma7shkf85937cbchfygd74&i=201403223kCqB3Ez&d=2625&sj=11&lang=ja&rel=1&from=11&cmt=1&tk=TlRBM09EQTNNekU9&tl=プリズン･ブレイク%20S1-01%20マイケル%20【吹替】',
        'md5': 'b8aae5334cb691bdb1193a88a6ab5d5a',
        'info_dict': {
            'id': '201403223kCqB3Ez',
            'ext': 'flv',
            'title': 'プリズン･ブレイク S1-01 マイケル 【吹替】',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        query = compat_parse_qs(mobj.group('query'))

        video_id = query['i'][-1]
        title = query.get('tl', ['FC2 video %s' % video_id])[0]

        sj = query.get('sj', [None])[0]
        thumbnail = None
        if sj:
            # See thumbnailImagePath() in ServerConst.as of flv2.swf
            thumbnail = 'http://video%s-thumbnail.fc2.com/up/pic/%s.jpg' % (
                sj, '/'.join((video_id[:6], video_id[6:8], video_id[-2], video_id[-1], video_id)))

        return {
            '_type': 'url_transparent',
            'ie_key': FC2IE.ie_key(),
            'url': 'fc2:%s' % video_id,
            'title': title,
            'thumbnail': thumbnail,
        }


class FC2LiveIE(InfoExtractor):
    _VALID_URL = r'https?://live\.fc2\.com/(?P<id>\d+)'
    IE_NAME = 'fc2:live'

    _TESTS = [{
        'url': 'https://live.fc2.com/57892267/',
        'info_dict': {
            'id': '57892267',
            'title': 'どこまで・・・',
            'uploader': 'あつあげ',
            'uploader_id': '57892267',
            'thumbnail': r're:https?://.+fc2.+',
        },
        'skip': 'livestream',
    }]

    def _real_extract(self, url):
        if not websockets:
            raise ExtractorError('websockets library is not available. Please install it.', expected=True)
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://live.fc2.com/%s/' % video_id, video_id)

        self._set_cookie('live.fc2.com', 'js-player_size', '1')

        member_api = self._download_json(
            'https://live.fc2.com/api/memberApi.php', video_id, data=urlencode_postdata({
                'channel': '1',
                'profile': '1',
                'user': '1',
                'streamid': video_id
            }), note='Requesting member info')

        control_server = self._download_json(
            'https://live.fc2.com/api/getControlServer.php', video_id, note='Downloading ControlServer data',
            data=urlencode_postdata({
                'channel_id': video_id,
                'mode': 'play',
                'orz': '',
                'channel_version': member_api['data']['channel_data']['version'],
                'client_version': '2.1.0\n [1]',
                'client_type': 'pc',
                'client_app': 'browser_hls',
                'ipv6': '',
            }), headers={'X-Requested-With': 'XMLHttpRequest'})
        self._set_cookie('live.fc2.com', 'l_ortkn', control_server['orz_raw'])

        ws_url = update_url_query(control_server['url'], {'control_token': control_server['control_token']})
        playlist_data = None

        self.to_screen('%s: Fetching HLS playlist info via WebSocket' % video_id)
        ws = WebSocketsWrapper(ws_url, {
            'Cookie': str(self._get_cookies('https://live.fc2.com/'))[12:],
            'Origin': 'https://live.fc2.com',
            'Accept': '*/*',
            'User-Agent': self.get_param('http_headers')['User-Agent'],
        })

        self.write_debug('Sending HLS server request')

        while True:
            recv = ws.recv()
            if not recv:
                continue
            data = self._parse_json(recv, video_id, fatal=False)
            if not data or not isinstance(data, dict):
                continue

            if data.get('name') == 'connect_complete':
                break
        ws.send(r'{"name":"get_hls_information","arguments":{},"id":1}')

        while True:
            recv = ws.recv()
            if not recv:
                continue
            data = self._parse_json(recv, video_id, fatal=False)
            if not data or not isinstance(data, dict):
                continue
            if data.get('name') == '_response_' and data.get('id') == 1:
                self.write_debug('Goodbye')
                playlist_data = data
                break
            self.write_debug('Server said: %s%s' % (recv[:100], '...' if len(recv) > 100 else ''))

        if not playlist_data:
            raise ExtractorError('Unable to fetch HLS playlist info via WebSocket')

        formats = []
        for name, playlists in playlist_data['arguments'].items():
            if not isinstance(playlists, list):
                continue
            for pl in playlists:
                if pl.get('status') == 0 and 'master_playlist' in pl.get('url'):
                    formats.extend(self._extract_m3u8_formats(
                        pl['url'], video_id, ext='mp4', m3u8_id=name, live=True,
                        headers={
                            'Origin': 'https://live.fc2.com',
                            'Referer': url,
                        }))

        for fmt in formats:
            fmt.update({
                'protocol': 'fc2_live',
                'ws': ws,
            })

        title = self._html_search_meta(('og:title', 'twitter:title'), webpage, 'live title', fatal=False)
        if not title:
            title = self._html_extract_title(webpage, 'html title', fatal=False)
            if title:
                # remove service name in <title>
                title = re.sub(r'\s+-\s+.+$', '', title)
        uploader = None
        if title:
            match = self._search_regex(r'^(.+?)\s*\[(.+?)\]$', title, 'title and uploader', default=None, group=(1, 2))
            if match and all(match):
                title, uploader = match

        live_info_view = self._search_regex(r'(?s)liveInfoView\s*:\s*({.+?}),\s*premiumStateView', webpage, 'user info', fatal=False) or None
        if live_info_view:
            # remove jQuery code from object literal
            live_info_view = re.sub(r'\$\(.+?\)[^,]+,', '"",', live_info_view)
            live_info_view = self._parse_json(js_to_json(live_info_view), video_id)

        return {
            'id': video_id,
            'title': title or traverse_obj(live_info_view, 'title'),
            'description': self._html_search_meta(
                ('og:description', 'twitter:description'),
                webpage, 'live description', fatal=False) or traverse_obj(live_info_view, 'info'),
            'formats': formats,
            'uploader': uploader or traverse_obj(live_info_view, 'name'),
            'uploader_id': video_id,
            'thumbnail': traverse_obj(live_info_view, 'thumb'),
            'is_live': True,
        }
