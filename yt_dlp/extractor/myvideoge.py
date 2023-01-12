from .common import InfoExtractor
from ..utils import js_to_json


class MyVideoGeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?myvideo\.ge/v/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.myvideo.ge/v/3941048',
        'md5': '8c192a7d2b15454ba4f29dc9c9a52ea9',
        'info_dict': {
            'id': '3941048',
            'ext': 'mp4',
            'title': 'The best prikol',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'md5:d72addd357b0dd914e704781f7f777d8',
            'description': 'md5:5c0371f540f5888d603ebfedd46b6df3'
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<h1[^>]*>([^<]+)</h1>', webpage, 'title')
        description = self._og_search_description(webpage)
        thumbnail = self._html_search_meta(['og:image'], webpage)
        uploader = self._search_regex(r'<a[^>]+class="mv_user_name"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False)

        jwplayer_sources = self._parse_json(
            self._search_regex(
                r"(?s)jwplayer\(\"mvplayer\"\).setup\(.*?sources: (.*?])", webpage, 'jwplayer sources'),
            video_id, transform_source=js_to_json)

        def _formats_key(f):
            if f['label'] == 'SD':
                return -1
            elif f['label'] == 'HD':
                return 1
            else:
                return 0

        jwplayer_sources = sorted(jwplayer_sources, key=_formats_key)

        formats = self._parse_jwplayer_formats(jwplayer_sources, video_id)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'formats': formats,
            'thumbnail': thumbnail
        }
