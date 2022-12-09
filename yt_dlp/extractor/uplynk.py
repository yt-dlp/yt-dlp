import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
    update_url_query,
)


class UplynkBaseIE(InfoExtractor):
    _UPLYNK_URL_RE = r'''(?x)
        https?://[\w-]+\.uplynk\.com/(?P<path>
            ext/[0-9a-f]{32}/(?P<external_id>[^/?&]+)|
            (?P<id>[0-9a-f]{32})
        )\.(?:m3u8|json)
        (?:.*?\bpbs=(?P<session_id>[^&]+))?'''

    def _extract_uplynk_info(self, url):
        uplynk_content_url, smuggled_data = unsmuggle_url(url, {})
        mobj = re.match(self._UPLYNK_URL_RE, uplynk_content_url)
        if not mobj:
            raise ExtractorError('Necessary parameters not found in Uplynk URL')
        path, external_id, video_id, session_id = mobj.group('path', 'external_id', 'id', 'session_id')
        display_id = video_id or external_id
        headers = traverse_obj(
            smuggled_data, {'Referer': 'Referer', 'Origin': 'Origin'}, casesense=False)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'http://content.uplynk.com/{path}.m3u8', display_id, 'mp4', headers=headers)
        if session_id:
            for f in formats:
                f['extra_param_to_segment_url'] = f'pbs={session_id}'
        asset = self._download_json(
            f'http://content.uplynk.com/player/assetinfo/{path}.json', display_id)
        if asset.get('error') == 1:
            msg = asset.get('msg') or 'unknown error'
            raise ExtractorError(f'{self.IE_NAME} said: {msg}', expected=True)

        return {
            'id': asset['asset'],
            'title': asset['desc'],
            'thumbnail': asset.get('default_poster_url'),
            'duration': float_or_none(asset.get('duration')),
            'uploader_id': asset.get('owner'),
            'formats': formats,
            'subtitles': subtitles,
        }


class UplynkIE(UplynkBaseIE):
    IE_NAME = 'uplynk'
    _VALID_URL = UplynkBaseIE._UPLYNK_URL_RE
    _TEST = {
        'url': 'http://content.uplynk.com/e89eaf2ce9054aa89d92ddb2d817a52e.m3u8',
        'info_dict': {
            'id': 'e89eaf2ce9054aa89d92ddb2d817a52e',
            'ext': 'mp4',
            'title': '030816-kgo-530pm-solar-eclipse-vid_web.mp4',
            'uploader_id': '4413701bf5a1488db55b767f8ae9d4fa',
            'duration': 530.2739166666679,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }

    def _real_extract(self, url):
        return self._extract_uplynk_info(url)


class UplynkPreplayIE(UplynkBaseIE):
    IE_NAME = 'uplynk:preplay'
    _VALID_URL = r'https?://[\w-]+\.uplynk\.com/preplay2?/(?P<path>ext/[0-9a-f]{32}/(?P<external_id>[^/?&]+)|(?P<id>[0-9a-f]{32}))\.json'

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        path, external_id, video_id = self._match_valid_url(url).groups()
        display_id = video_id or external_id
        preplay = self._download_json(url, display_id)
        content_url = f'http://content.uplynk.com/{path}.m3u8'
        session_id = preplay.get('sid')
        if session_id:
            content_url = update_url_query(content_url, {'pbs': session_id})
        return self._extract_uplynk_info(smuggle_url(content_url, smuggled_data))
