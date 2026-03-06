from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
    str_or_none,
    unescapeHTML,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class PeriscopeBaseIE(InfoExtractor):
    _M3U8_HEADERS = {
        'Referer': 'https://www.periscope.tv/',
    }

    def _call_api(self, method, query, item_id):
        return self._download_json(
            f'https://api.periscope.tv/api/v2/{method}',
            item_id, query=query)

    def _parse_broadcast_data(self, broadcast, video_id):
        return {
            'display_id': video_id,
            'live_status': {
                'running': 'is_live',
                'not_started': 'is_upcoming',
            }.get(traverse_obj(broadcast, ('state', {str.lower}))) or 'was_live',
            **traverse_obj(broadcast, {
                'id': ('id', {str_or_none}),
                'title': ('status', {clean_html}, filter),
                'concurrent_view_count': ('total_watching', {int_or_none}),
                'release_timestamp': (('scheduled_start_ms', 'start_ms'), {int_or_none(scale=1000)}, any),
                'tags': ('tags', ..., {clean_html}, filter),
                'thumbnail': (('image_url', 'image_url_medium', 'image_url_small'), {url_or_none}, any),
                'timestamp': ((('created_at', {parse_iso8601}), ('created_at_ms', {int_or_none(scale=1000)})), any),
                'uploader': ('user_display_name', {clean_html}, filter),
                'uploader_id': ('username', {clean_html}, filter),
                'view_count': ('total_watched', {int_or_none}),
            }),
        }

    @staticmethod
    def _extract_common_format_info(broadcast):
        return broadcast.get('state').lower(), int_or_none(broadcast.get('width')), int_or_none(broadcast.get('height'))

    @staticmethod
    def _add_width_and_height(f, width, height):
        for key, val in (('width', width), ('height', height)):
            if not f.get(key):
                f[key] = val

    def _extract_pscp_m3u8_formats(self, m3u8_url, video_id, format_id, state, width, height, fatal=True):
        m3u8_formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4',
            entry_protocol='m3u8_native'
            if state in ('ended', 'timed_out') else 'm3u8',
            m3u8_id=format_id, fatal=fatal, headers=self._M3U8_HEADERS)
        if len(m3u8_formats) == 1:
            self._add_width_and_height(m3u8_formats[0], width, height)
        for f in m3u8_formats:
            f.setdefault('http_headers', {}).update(self._M3U8_HEADERS)
        return m3u8_formats


class PeriscopeIE(PeriscopeBaseIE):
    IE_DESC = 'Periscope'
    IE_NAME = 'periscope'
    _VALID_URL = r'https?://(?:www\.)?(?:periscope|pscp)\.tv/[^/]+/(?P<id>[^/?#]+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=([\'"])(?P<url>(?:https?:)?//(?:www\.)?(?:periscope|pscp)\.tv/(?:(?!\1).)+)\1']
    _TESTS = [{
        'url': 'https://www.periscope.tv/LularoeHusbandMike/1mrGmgaXAVqxy',
        'info_dict': {
            'id': '1mrGmgaXAVqxy',
            'ext': 'mp4',
            'title': '🎉👍🏼 BROWSE OUR ENTIRE 1,900 +PIECE INVENTORY! 👍🏼🎉 #lularoe',
            'live_status': 'was_live',
            'tags': 'count:1',
            'thumbnail': r're:https?://prod-fastly-us-east-1\.video\.pscp\.tv/.+',
            'timestamp': 1498621952,
            'upload_date': '20170628',
            'uploader': 'LuLaRoe Husband Mike',
            'uploader_id': 'LularoeHusbandMike',
        },
    }, {
        'url': 'https://www.periscope.tv/w/1ZkKzPbMVggJv',
        'only_matching': True,
    }, {
        'url': 'https://www.periscope.tv/bastaakanoggano/1OdKrlkZZjOJX',
        'only_matching': True,
    }, {
        'url': 'https://www.periscope.tv/w/1ZkKzPbMVggJv',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        token = self._match_id(url)

        stream = self._call_api(
            'accessVideoPublic', {'broadcast_id': token}, token)

        broadcast = stream['broadcast']
        info = self._parse_broadcast_data(broadcast, token)

        state = broadcast.get('state').lower()
        width = int_or_none(broadcast.get('width'))
        height = int_or_none(broadcast.get('height'))

        def add_width_and_height(f):
            for key, val in (('width', width), ('height', height)):
                if not f.get(key):
                    f[key] = val

        video_urls = set()
        formats = []
        for format_id in ('replay', 'rtmp', 'hls', 'https_hls', 'lhls', 'lhlsweb'):
            video_url = stream.get(format_id + '_url')
            if not video_url or video_url in video_urls:
                continue
            video_urls.add(video_url)
            if format_id != 'rtmp':
                m3u8_formats = self._extract_pscp_m3u8_formats(
                    video_url, token, format_id, state, width, height, False)
                formats.extend(m3u8_formats)
                continue
            rtmp_format = {
                'url': video_url,
                'ext': 'flv' if format_id == 'rtmp' else 'mp4',
            }
            self._add_width_and_height(rtmp_format)
            formats.append(rtmp_format)

        info['formats'] = formats
        return info


class PeriscopeUserIE(PeriscopeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?(?:periscope|pscp)\.tv/(?P<id>[^/]+)/?$'
    IE_DESC = 'Periscope user videos'
    IE_NAME = 'periscope:user'

    _TEST = {
        'url': 'https://www.periscope.tv/LularoeHusbandMike/',
        'info_dict': {
            'id': 'LularoeHusbandMike',
            'title': 'LULAROE HUSBAND MIKE',
            'description': 'md5:6cf4ec8047768098da58e446e82c82f0',
        },
        # Periscope only shows videos in the last 24 hours, so it's possible to
        # get 0 videos
        'playlist_mincount': 0,
    }

    def _real_extract(self, url):
        user_name = self._match_id(url)

        webpage = self._download_webpage(url, user_name)

        data_store = self._parse_json(
            unescapeHTML(self._search_regex(
                r'data-store=(["\'])(?P<data>.+?)\1',
                webpage, 'data store', default='{}', group='data')),
            user_name)

        user = next(iter(data_store['UserCache']['users'].values()))['user']
        user_id = user['id']
        session_id = data_store['SessionToken']['public']['broadcastHistory']['token']['session_id']

        broadcasts = self._call_api(
            'getUserBroadcastsPublic',
            {'user_id': user_id, 'session_id': session_id},
            user_name)['broadcasts']

        broadcast_ids = [
            broadcast['id'] for broadcast in broadcasts if broadcast.get('id')]

        title = user.get('display_name') or user.get('username') or user_name
        description = user.get('description')

        entries = [
            self.url_result(
                f'https://www.periscope.tv/{user_name}/{broadcast_id}')
            for broadcast_id in broadcast_ids]

        return self.playlist_result(entries, user_id, title, description)
