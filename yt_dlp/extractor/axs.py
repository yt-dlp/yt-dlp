from .common import InfoExtractor
from ..utils import (
    float_or_none,
    js_to_json,
    parse_iso8601,
)


class AxsIE(InfoExtractor):
    IE_NAME = 'axs.tv'
    _VALID_URL = r'https?://(?:www\.)?axs\.tv/(?:channel/[^/]+/)?video/(?P<id>[^?/]+)'
    _META_URL = 'https://api.myspotlight.tv/dotplayer/video/%s/%s?device_type=desktop_web'

    _TESTS = [{
        'url': 'https://www.axs.tv/video/5f4dc776b70e4f1c194f22ef/',
        'md5': '8d97736ae8e50c64df528e5e676778cf',
        'info_dict': {
            'id': '5f4dc776b70e4f1c194f22ef',
            'title': 'Small Town',
            'ext': 'mp4',
            'description': 'md5:e314d28bfaa227a4d7ec965fae19997f',
            'upload_date': '20230602',
            'timestamp': 1685729564,
            'duration': 1284.216,
            'channel': 'Rock & Roll Road Trip with Sammy Hagar',
            'season': 2,
            'episode': '3',
            'thumbnail': 'https://images.dotstudiopro.com/5f4e9d330a0c3b295a7e8394',
        },
    }, {
        'url': 'https://www.axs.tv/channel/rock-star-interview/video/daryl-hall',
        'md5': '300ae795cd8f9984652c0949734ffbdc',
        'info_dict': {
            'id': '5f488148b70e4f392572977c',
            'title': 'Daryl Hall',
            'ext': 'mp4',
            'description': 'md5:e54ecaa0f4b5683fc9259e9e4b196628',
            'upload_date': '20230214',
            'timestamp': 1676403615,
            'duration': 2570.668,
            'channel': 'The Big Interview with Dan Rather',
            'season': 3,
            'episode': '5',
            'thumbnail': 'https://images.dotstudiopro.com/5f4d1901f340b50d937cec32',
        },
    }]

    def _real_extract(self, url):
        initial_id = self._match_id(url)
        webpage = self._download_webpage(url, initial_id)

        webpage_json_data = self._search_json(
            r'mountObj\s*=', webpage, 'video ID data', initial_id,
            transform_source=js_to_json, default={})
        video_id = webpage_json_data['video_id']
        company_id = webpage_json_data['company_id']

        meta_url = self._META_URL % (company_id, video_id)
        meta = self._download_json(meta_url, video_id)['video']

        format_url = meta['video_m3u8']
        formats = self._extract_m3u8_formats(
            format_url, video_id, 'mp4', m3u8_id='hls',
            entry_protocol='m3u8_native', fatal=False)

        subtitles = {}
        for cc in meta.get('closeCaption'):
            subtitles.setdefault(cc.get('srtShortLang') or 'en', []).append(
                {'ext': cc.get('srtExt'), 'url': cc['srtPath']})

        return {
            'id': video_id,
            'formats': formats,
            'title': meta['title'],
            'description': meta.get('description'),
            'channel': meta.get('seriestitle'),
            'season': meta.get('season'),
            'episode': meta.get('episode'),
            'duration': float_or_none(meta.get('duration')),
            'timestamp': parse_iso8601(meta.get('updated_at')),
            'thumbnail': meta.get('thumb'),
            'subtitles': subtitles,
        }
