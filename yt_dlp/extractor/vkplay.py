from .common import InfoExtractor
from ..utils import (
    int_or_none,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class VKPlayIE(InfoExtractor):
    _VALID_URL = r'https?://vkplay\.live/\w+/record/(?P<id>[a-f0-9\-]+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        initial_state_json = self._search_regex(r'id="initial-state"[^>]*>([^<]+)</script>', webpage, 'initial_state')
        initial_state = self._parse_json(initial_state_json, video_id)
        record_info = traverse_obj(initial_state, ('record', 'currentRecord', 'data'))
        playurls = traverse_obj(record_info, ('data', 0, 'playerUrls', ..., {
            'url': ('url', {url_or_none}),
            'format_id': ('type', {str_or_none}),
        }))
        formats = []
        for playurl in playurls:
            if not playurl.get('url', None):
                continue
            elif '.m3u8' in playurl['url']:
                formats.extend(self._extract_m3u8_formats(playurl['url'], video_id))
            else:
                formats.append(playurl)

        meta = {
            'id': video_id,
            'formats': formats,
            **traverse_obj(record_info, {
                'title': ('title', {str}),
                'thumbnail': ('previewUrl', {url_or_none}),
                'release_timestamp': ('startTime'),
                'uploader': ('blog', 'owner', 'name', {str_or_none}),
                'uploader_id': ('blog', 'owner', 'name', {str_or_none}),
                'duration': ('duration', {int_or_none}),
                'view_count': ('count', 'views', {int_or_none}),
                'like_count': ('count', 'likes', {int_or_none}),
                'categories': ('category', 'title', {lambda i: [str_or_none(i)]}),
            })
        }
        print(meta)
        return meta
