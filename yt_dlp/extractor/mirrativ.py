from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    dict_get,
    traverse_obj,
    try_get,
)


class MirrativBaseIE(InfoExtractor):
    def assert_error(self, response):
        error_message = traverse_obj(response, ('status', 'error'))
        if error_message:
            raise ExtractorError('Mirrativ says: %s' % error_message, expected=True)


class MirrativIE(MirrativBaseIE):
    IE_NAME = 'mirrativ'
    _VALID_URL = r'https?://(?:www\.)?mirrativ\.com/live/(?P<id>[^/?#&]+)'
    LIVE_API_URL = 'https://www.mirrativ.com/api/live/live?live_id=%s'

    TESTS = [{
        'url': 'https://mirrativ.com/live/POxyuG1KmW2982lqlDTuPw',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://www.mirrativ.com/live/%s' % video_id, video_id)
        live_response = self._download_json(self.LIVE_API_URL % video_id, video_id)
        self.assert_error(live_response)

        hls_url = dict_get(live_response, ('archive_url_hls', 'streaming_url_hls'))
        is_live = bool(live_response.get('is_live'))
        was_live = bool(live_response.get('is_archive'))
        if not hls_url:
            raise ExtractorError('Neither archive nor live is available.', expected=True)

        formats = self._extract_m3u8_formats(
            hls_url, video_id,
            ext='mp4', entry_protocol='m3u8_native',
            m3u8_id='hls', live=is_live)
        rtmp_url = live_response.get('streaming_url_edge')
        if rtmp_url:
            keys_to_copy = ('width', 'height', 'vcodec', 'acodec', 'tbr')
            fmt = {
                'format_id': 'rtmp',
                'url': rtmp_url,
                'protocol': 'rtmp',
                'ext': 'mp4',
            }
            fmt.update({k: traverse_obj(formats, (0, k)) for k in keys_to_copy})
            formats.append(fmt)
        self._sort_formats(formats)

        title = self._og_search_title(webpage, default=None) or self._search_regex(
            r'<title>\s*(.+?) - Mirrativ\s*</title>', webpage) or live_response.get('title')
        description = live_response.get('description')
        thumbnail = live_response.get('image_url')

        duration = try_get(live_response, lambda x: x['ended_at'] - x['started_at'])
        view_count = live_response.get('total_viewer_num')
        release_timestamp = live_response.get('started_at')
        timestamp = live_response.get('created_at')

        owner = live_response.get('owner', {})
        uploader = owner.get('name')
        uploader_id = owner.get('user_id')

        return {
            'id': video_id,
            'title': title,
            'is_live': is_live,
            'description': description,
            'formats': formats,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'duration': duration,
            'view_count': view_count,
            'release_timestamp': release_timestamp,
            'timestamp': timestamp,
            'was_live': was_live,
        }


class MirrativUserIE(MirrativBaseIE):
    IE_NAME = 'mirrativ:user'
    _VALID_URL = r'https?://(?:www\.)?mirrativ\.com/user/(?P<id>\d+)'
    LIVE_HISTORY_API_URL = 'https://www.mirrativ.com/api/live/live_history?user_id=%s&page=%d'
    USER_INFO_API_URL = 'https://www.mirrativ.com/api/user/profile?user_id=%s'

    _TESTS = [{
        # Live archive is available up to 3 days
        # see: https://helpfeel.com/mirrativ/%E9%8C%B2%E7%94%BB-5e26d3ad7b59ef0017fb49ac (Japanese)
        'url': 'https://www.mirrativ.com/user/110943130',
        'note': 'multiple archives available',
        'only_matching': True,
    }]

    def _entries(self, user_id):
        page = 1
        while page is not None:
            api_response = self._download_json(
                self.LIVE_HISTORY_API_URL % (user_id, page), user_id,
                note='Downloading page %d' % page)
            self.assert_error(api_response)
            lives = api_response.get('lives')
            if not lives:
                break
            for live in lives:
                if not live.get('is_archive') and not live.get('is_live'):
                    # neither archive nor live is available, so skip it
                    # or the service will ban your IP address for a while
                    continue
                live_id = live.get('live_id')
                url = 'https://www.mirrativ.com/live/%s' % live_id
                yield self.url_result(url, video_id=live_id, video_title=live.get('title'))
            page = api_response.get('next_page')

    def _real_extract(self, url):
        user_id = self._match_id(url)
        user_info = self._download_json(
            self.USER_INFO_API_URL % user_id, user_id,
            note='Downloading user info', fatal=False)
        self.assert_error(user_info)

        uploader = user_info.get('name')
        description = user_info.get('description')

        entries = self._entries(user_id)
        return self.playlist_result(entries, user_id, uploader, description)
