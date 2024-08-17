import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    unescapeHTML,
)


class ReutersIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?reuters\.com/.*?\?.*?videoId=(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://www.reuters.com/video/2016/05/20/san-francisco-police-chief-resigns?videoId=368575562',
        'md5': '8015113643a0b12838f160b0b81cc2ee',
        'info_dict': {
            'id': '368575562',
            'ext': 'mp4',
            'title': 'San Francisco police chief resigns',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            f'http://www.reuters.com/assets/iframe/yovideo?videoId={video_id}', video_id)
        video_data = js_to_json(self._search_regex(
            r'(?s)Reuters\.yovideo\.drawPlayer\(({.*?})\);',
            webpage, 'video data'))

        def get_json_value(key, fatal=False):
            return self._search_regex(rf'"{key}"\s*:\s*"([^"]+)"', video_data, key, fatal=fatal)

        title = unescapeHTML(get_json_value('title', fatal=True))
        mmid, fid = re.search(r',/(\d+)\?f=(\d+)', get_json_value('flv', fatal=True)).groups()

        mas_data = self._download_json(
            f'http://mas-e.cds1.yospace.com/mas/{mmid}/{fid}?trans=json',
            video_id, transform_source=js_to_json)
        formats = []
        for f in mas_data:
            f_url = f.get('url')
            if not f_url:
                continue
            method = f.get('method')
            if method == 'hls':
                formats.extend(self._extract_m3u8_formats(
                    f_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False))
            else:
                container = f.get('container')
                ext = '3gp' if method == 'mobile' else container
                formats.append({
                    'format_id': ext,
                    'url': f_url,
                    'ext': ext,
                    'container': container if method != 'mobile' else None,
                })

        return {
            'id': video_id,
            'title': title,
            'thumbnail': get_json_value('thumb'),
            'duration': int_or_none(get_json_value('seconds')),
            'formats': formats,
        }
