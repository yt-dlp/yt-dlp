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


class PandaTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|m\.)?pandalive\.co\.kr/play/(?P<id>[\da-z]+)'
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
        channel_id = self._match_id(url)
        http_headers = {'Origin': 'https://www.pandalive.co.kr'}

        video_meta = self._download_json(
            'https://api.pandalive.co.kr/v1/live/play', channel_id,
            'Downloading video meta data', 'Unable to download video meta data',
            data=urlencode_postdata({
                'action': 'watch',
                'userId': channel_id,
                'password': self.get_param('videopassword'),
                'shareLinkType': '',
            }), expected_status=400)

        if not video_meta.get('result'):
            error_code = traverse_obj(video_meta, ('errorData', 'code', {str}))
            if error_code == 'castEnd':
                raise UserNotLive(video_id=channel_id)
            elif error_code == 'needAdult':
                self.raise_login_required('Adult verification is required for this stream')
            elif error_code == 'needLogin':
                self.raise_login_required('Login is required for this stream')
            elif error_code == 'needCoinPurchase':
                raise ExtractorError('Coin purchase is required for this stream', expected=True)
            elif error_code == 'needUnlimitItem':
                raise ExtractorError('Ticket purchase is required for this stream', expected=True)
            elif error_code == 'wrongPw':
                raise ExtractorError('Password protected video, use --video-password <password>', expected=True)
            else:
                raise ExtractorError(f'API returned an error code: {error_code}')

        return {
            'id': channel_id,
            'is_live': True,
            'formats': self._extract_m3u8_formats(
                video_meta['PlayList']['hls'][0]['url'], channel_id, 'mp4', headers=http_headers, live=True),
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
