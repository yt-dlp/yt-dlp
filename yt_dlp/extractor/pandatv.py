from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
    int_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
    urlencode_postdata,
)


class PandatvLiveIE(InfoExtractor):
    _VALID_URL = r'(?P<base_url>https?://(?:www\.|m\.)?pandalive\.co\.kr)/play/(?P<id>[\da-z]+)'
    _TESTS = [{
        'url': 'https://www.pandalive.co.kr/play/bebenim',
        'info_dict': {
            'id': 'bebenim',
            'ext': 'mp4',
            'channel': '릴리ෆ',
            'title': r're:앙앙❤ \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'thumbnail': r're:https://cdn\.pandalive\.co\.kr/ivs/v1/.+/thumb.jpg',
            'concurrent_view_count': int,
            'like_count': int,
            'live_status': 'is_live',
            'upload_date': str,
        },
        'skip': 'The channel is not currently live',
    }]

    def _real_extract(self, url):
        base_url, channel_id = self._match_valid_url(url).groups()
        http_headers = {'Origin': base_url}

        # Prepare POST data
        post_data = {'action': 'watch', 'userId': channel_id, 'password': '', 'shareLinkType': ''}
        post_data_bytes = urlencode_postdata(post_data)

        # Fetch video metadata
        video_meta = self._download_json(
            'https://api.pandalive.co.kr/v1/live/play', channel_id, 'Downloading video meta data',
            errnote=' Unable to download video meta data', data=post_data_bytes, expected_status=(200, 400))

        # Check video metadata
        if not video_meta.get('result'):
            if traverse_obj(video_meta, ('errorData', 'code')) == 'castEnd':
                raise UserNotLive(video_id=channel_id)
            elif traverse_obj(video_meta, ('errorData', 'code')) == 'needAdult':
                raise ExtractorError(
                    'Adult verification is required. Check `--cookies` or `--cookies-from-browser` '
                    'method in https://github.com/yt-dlp/yt-dlp#filesystem-options', expected=True)

        return {
            'id': channel_id,
            'is_live': True,
            'formats': self._extract_m3u8_formats(
                traverse_obj(video_meta, ('PlayList', 'hls', 0, 'url')), channel_id, headers=http_headers,
                ext='mp4', fatal=False, live=True),
            'http_headers': http_headers,
            **traverse_obj(video_meta.get('media'), {
                'title': ('title', {str}),
                'upload_date': ('startTime', {unified_strdate}),
                'thumbnail': ('ivsThumbnail', {url_or_none}),
                'channel': ('userNick', {str}),
                'concurrent_view_count': ('user', {int_or_none}),
                'like_count': ('likeCnt', {int_or_none}),
            }),
        }
