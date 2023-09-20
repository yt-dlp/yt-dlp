from .common import InfoExtractor
from ..utils import (
    float_or_none,
    js_to_json,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class AxsIE(InfoExtractor):
    IE_NAME = 'axs.tv'
    _VALID_URL = r'https?://(?:www\.)?axs\.tv/(?:channel/(?:[^/?#]+/)+)?video/(?P<id>[^/?#]+)'

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
            'series': 'Rock & Roll Road Trip with Sammy Hagar',
            'season': 2,
            'episode': '3',
            'thumbnail': 'https://images.dotstudiopro.com/5f4e9d330a0c3b295a7e8394',
        },
    }, {
        'url': 'https://www.axs.tv/channel/rock-star-interview/video/daryl-hall',
        'md5': '300ae795cd8f9984652c0949734ffbdc',
        'info_dict': {
            'id': '5f488148b70e4f392572977c',
            'display_id': 'daryl-hall',
            'title': 'Daryl Hall',
            'ext': 'mp4',
            'description': 'md5:e54ecaa0f4b5683fc9259e9e4b196628',
            'upload_date': '20230214',
            'timestamp': 1676403615,
            'duration': 2570.668,
            'series': 'The Big Interview with Dan Rather',
            'season': 3,
            'episode': '5',
            'thumbnail': 'https://images.dotstudiopro.com/5f4d1901f340b50d937cec32',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        webpage_json_data = self._search_json(
            r'mountObj\s*=', webpage, 'video ID data', display_id,
            transform_source=js_to_json)
        video_id = webpage_json_data['video_id']
        company_id = webpage_json_data['company_id']

        meta = self._download_json(
            f'https://api.myspotlight.tv/dotplayer/video/{company_id}/{video_id}',
            video_id, query={'device_type': 'desktop_web'})['video']

        formats = self._extract_m3u8_formats(
            meta['video_m3u8'], video_id, 'mp4', m3u8_id='hls')

        subtitles = {}
        for cc in traverse_obj(meta, ('closeCaption', lambda _, v: url_or_none(v['srtPath']))):
            subtitles.setdefault(cc.get('srtShortLang') or 'en', []).append(
                {'ext': cc.get('srtExt'), 'url': cc['srtPath']})

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            **traverse_obj(meta, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'series': ('seriestitle', {str}),
                'season': ('season', {int}),
                'episode': ('episode', {str}),
                'duration': ('duration', {float_or_none}),
                'timestamp': ('updated_at', {parse_iso8601}),
                'thumbnail': ('thumb', {url_or_none}),
            }),
            'subtitles': subtitles,
        }
