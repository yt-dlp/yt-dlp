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
            raise ExtractorError(f'Mirrativ says: {error_message}', expected=True)


class MirrativIE(MirrativBaseIE):
    IE_NAME = 'mirrativ'
    _VALID_URL = r'https?://(?:www\.)?mirrativ\.com/live/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://mirrativ.com/live/UQomuS7EMgHoxRHjEhNiHw',
        'info_dict': {
            'id': 'UQomuS7EMgHoxRHjEhNiHw',
            'title': 'ねむいぃ、。『参加型』🔰jcが初めてやるCOD✨初見さん大歓迎💗',
            'is_live': True,
            'description': 'md5:bfcd8f77f2fab24c3c672e5620f3f16e',
            'thumbnail': r're:https?://.+',
            'uploader': '# あ ち ゅ 。💡',
            'uploader_id': '118572165',
            'duration': None,
            'view_count': 1241,
            'release_timestamp': 1646229192,
            'timestamp': 1646229167,
            'was_live': False,
        },
        'skip': 'livestream',
    }, {
        'url': 'https://mirrativ.com/live/POxyuG1KmW2982lqlDTuPw',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://www.mirrativ.com/live/{video_id}', video_id)
        live_response = self._download_json(f'https://www.mirrativ.com/api/live/live?live_id={video_id}', video_id)
        self.assert_error(live_response)

        hls_url = dict_get(live_response, ('archive_url_hls', 'streaming_url_hls'))
        is_live = bool(live_response.get('is_live'))
        if not hls_url:
            raise ExtractorError('Neither archive nor live is available.', expected=True)

        formats = self._extract_m3u8_formats(
            hls_url, video_id,
            ext='mp4', entry_protocol='m3u8_native',
            m3u8_id='hls', live=is_live)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None) or self._search_regex(
                r'<title>\s*(.+?) - Mirrativ\s*</title>', webpage) or live_response.get('title'),
            'is_live': is_live,
            'description': live_response.get('description'),
            'formats': formats,
            'thumbnail': live_response.get('image_url'),
            'uploader': traverse_obj(live_response, ('owner', 'name')),
            'uploader_id': traverse_obj(live_response, ('owner', 'user_id')),
            'duration': try_get(live_response, lambda x: x['ended_at'] - x['started_at']) if not is_live else None,
            'view_count': live_response.get('total_viewer_num'),
            'release_timestamp': live_response.get('started_at'),
            'timestamp': live_response.get('created_at'),
            'was_live': bool(live_response.get('is_archive')),
        }


class MirrativUserIE(MirrativBaseIE):
    IE_NAME = 'mirrativ:user'
    _VALID_URL = r'https?://(?:www\.)?mirrativ\.com/user/(?P<id>\d+)'

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
                f'https://www.mirrativ.com/api/live/live_history?user_id={user_id}&page={page}', user_id,
                note=f'Downloading page {page}')
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
                url = f'https://www.mirrativ.com/live/{live_id}'
                yield self.url_result(url, video_id=live_id, video_title=live.get('title'))
            page = api_response.get('next_page')

    def _real_extract(self, url):
        user_id = self._match_id(url)
        user_info = self._download_json(
            f'https://www.mirrativ.com/api/user/profile?user_id={user_id}', user_id,
            note='Downloading user info', fatal=False)
        self.assert_error(user_info)

        return self.playlist_result(
            self._entries(user_id), user_id,
            user_info.get('name'), user_info.get('description'))
