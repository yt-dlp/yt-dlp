from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    traverse_obj,
)


class NZOnScreenIE(InfoExtractor):
    _VALID_URL = r'^https://www.nzonscreen.com/title/(?P<id>[^\?]+)'
    _TESTS = [{
        'url': 'https://www.nzonscreen.com/title/shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
        'md5': 'a0375e9b6f14b235438506cb0aee974c',
        'info_dict': {
            'id': 'shoop-shoop-diddy-wop-cumma-cumma-wang-dang-1982',
            'ext': 'mp4',
            'title': 'Monte Video - "Shoop Shoop, Diddy Wop"',
            'format_id': 'lo_res'
        },
    }, {
        'url': 'https://www.nzonscreen.com/title/shes-a-mod-1964?collection=best-of-the-60s',
        'md5': 'e8a56d7d02cdcdc5d6f8897e2532e157',
        'info_dict': {
            'id': 'shes-a-mod-1964',
            'ext': 'mp4',
            'title': 'Ray Columbus - \'She\'s A Mod\'',
            'format_id': 'lo_res'
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        playlist = self._parse_json(self._html_search_regex(
            r'data-video-config=\'(.+?)\'', webpage, 'media data'),
            video_id)

        title = traverse_obj(playlist, 'label') or traverse_obj(playlist, 'description') or ''
        if not title:
            page_title = self._html_extract_title(webpage, default=None) or self._og_search_title(
                webpage, default=None)
            if page_title and '|' in page_title:
                title = page_title.split('|')[0].strip()

        playlist_formats = traverse_obj(playlist, 'h264', default=None)

        if not playlist_formats:
            raise ExtractorError('No video formats found')

        formats = []
        for format_id in ['lo_res', 'hd_res', 'hi_res']:
            if format_id in playlist_formats:
                formats.append({
                    'url': traverse_obj(playlist_formats, format_id),
                    'format_id': format_id,
                    'ext': 'mp4',
                    'http_headers': {
                        'Referer': 'https://www.nzonscreen.com/',
                        'Origin': 'https://www.nzonscreen.com/',
                    }
                })

        return {
            'id': video_id,
            'title': title,
            '_type': 'video',
            'formats': formats,
        }
