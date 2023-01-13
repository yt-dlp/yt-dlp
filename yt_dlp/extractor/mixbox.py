import hashlib
import re

from .common import InfoExtractor


class MixBoxHomepageIE(InfoExtractor):
    IE_NAME = 'MixBox:homepage'
    IE_DESC = 'ミックスボックス'
    _VALID_URL = r'https?://mixbox\.live/?$'
    _TESTS = [{
        'url': 'https://mixbox.live/',
        'info_dict': {
            'id': 'mixbox-live',
            'title': 'MixBox',
            'ext': 'ts',
            'live_status': 'is_live',
        },
    }]

    def _real_extract(self, url):
        video_id = 'mixbox-live'

        asset_js_urls = re.findall(
            r'<script src="(/assets/.+?\.js)"', self._download_webpage(url, video_id))
        asset_js_urls.reverse()  # the live video info always seems to be placed in the last file

        live_video_key, live_video_url = '', ''
        for asset_js_url in asset_js_urls:
            asset_js_content = self._download_webpage(
                f'https://mixbox.live/{asset_js_url}', video_id,
                note='Fetching asset js file', errnote='Unable to fetch asset js file')
            live_video_key, live_video_url = self._search_regex(
                r'LIVE_VIDEO_key:\s*"(?P<key>[\dA-Z]{64})".+LIVE_VIDEO_url:\s*"(?P<url>https://[^"]+)"',
                asset_js_content, name='live video info', fatal=False,
                group=('key', 'url'), default=(None, None))
            if live_video_key and live_video_url:
                break
        if not live_video_key or not live_video_url:
            self.raise_no_formats('no live video info found')

        a_string = 'just a meaningless but non-empty string'
        bearer_token = hashlib.sha256((live_video_key + a_string).encode()).hexdigest().upper()

        live_video_json = self._download_json(
            live_video_url, video_id=video_id, query={'hash': a_string},
            note='Fetching playlist json', errnote='Unable to fetch playlist json',
            headers={'Authorization': f'Bearer {bearer_token}'})

        m3u8_url = live_video_json.get('url')
        if not m3u8_url:
            self.raise_no_formats('no m3u8 playlist found')

        return {
            'id': video_id,
            'title': 'MixBox',
            'formats': self._extract_m3u8_formats(m3u8_url, video_id=video_id, ext='ts'),
            'live_status': 'is_live',
        }
