
from .common import InfoExtractor
from ..utils import NO_DEFAULT, float_or_none, format_field, int_or_none, traverse_obj, unified_timestamp


class SkoolIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?skool\.com/(?P<group>[^/]+)/classroom/(?P<class>[^/?]+)(?:\?id=(?P<id>[^&]+))?'
    _REQUIRED_COOKIE = 'auth_token'
    _TESTS = [{
        'url': 'https://www.skool.com/skoolers/classroom/c4b8d595?md=86ca3282abf4421687df974a7cac98db',
        'info_dict': {
            'id': '2694137c46c7456d823ded9ac8ea716f',
            'ext': 'mp4',
            'title': '1. Context - $100M Money Models · Skoolers',
            'description': 'Private club for skool owners. Let\'s build communities together.',
            'duration': 706666,
            'aspect_ratio': 1.78,
            'thumbnail': r're:^https://thumb\.video\.skool\.com/[^/]+/00000000\.jpg\?token=.*',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _search_data(self, webpage, video_id, *, fatal=True, default=NO_DEFAULT, **kw):
        return self._search_nextjs_data(webpage, video_id, fatal=fatal, default=default, **kw)

    def _real_initialize(self):
        # Check if the required cookie is present
        if 'auth_token' not in self._get_cookies(self._downloader._url):
            self.raise_login_required(metadata_available=False)

    def _real_extract(self, url):
        classroom, video_id = self._match_valid_url(url).group('class', 'id')
        webpage = self._download_webpage(url, video_id or classroom)

        next_data = self._search_nextjs_data(webpage, video_id, default={})

        video_data = traverse_obj(next_data, ('props', 'pageProps', 'video', {dict})) or {}

        video_id = video_data.get('id')
        playback_id = video_data.get('playbackId')
        playback_token = video_data.get('playbackToken')

        formats = []
        subtitles = {}

        if playback_id and playback_token:
            m3u8_url = f'https://stream.video.skool.com/{playback_id}.m3u8?token={playback_token}'
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False, headers={
                    'Referer': url,
                })
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'title': traverse_obj(next_data, ('props', 'pageProps', 'settings', 'pageTitle')),
            'description': self._og_search_description(webpage, default=None),
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': {
                'Referer': url,
            },
            'duration': int_or_none(video_data.get('duration')),
            'aspect_ratio': float_or_none(video_data.get('aspectRatio')),
            'thumbnail': format_field(
                video_data, 'thumbnailToken',
                f'https://thumb.video.skool.com/{playback_id}/00000000.jpg?token=%s',
                default=None) if playback_id else None,
            'expire': unified_timestamp(video_data.get('expire')),
        }
