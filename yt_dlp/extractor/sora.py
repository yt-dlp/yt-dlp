import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    lowercase_escape,
    unescapeHTML,
    url_or_none,
)


class SoraExtractorIE(InfoExtractor):
    _VALID_URL = r'https://sora\.chatgpt\.com/p/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://sora.chatgpt.com/p/s_68ddd8c38ae8819180aa11a37b1d1e88',
        'info_dict': {
            'id': 's_68ddd8c38ae8819180aa11a37b1d1e88',
            'ext': 'mp4',
            'title': 'unitof on Sora',
            'description': 'md5:d7a614c169fa6da1dbff019e736bd2b0',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, impersonate=True)

        title = self._og_search_title(webpage)
        description = self._og_search_description(webpage)

        # - https://videos.openai.com/vg-assets/.../videos/00000/src.mp4?... (unwatermarked)
        # - https://videos.openai.com/vg-assets/.../videos/00000_wm/src.mp4?... (watermarked)
        url_pattern = r'https?://videos\.openai\.com/[^\s"\'<>]*src\.mp4[^\s"\'<>]*'

        found_urls = [
            unescapeHTML(lowercase_escape(unescapeHTML(m)))
            for m in re.findall(url_pattern, webpage)
        ]

        formats = []
        for vurl in found_urls:
            vurl = url_or_none(vurl)
            if not vurl:
                continue
            parsed = urllib.parse.urlparse(vurl)
            decoded_path = urllib.parse.unquote(parsed.path or '')

            # We have not yet figured out signed unwatermarked URLs are generated in iOS app, due to SSL pinning
            is_wm = ('/00000_wm/' in decoded_path)
            formats.append({
                'url': vurl,
                'ext': 'mp4',
                'format_id': 'watermarked' if is_wm else 'unwatermarked',
                'preference': -10 if is_wm else 10,
            })

        if formats:
            return {
                'id': video_id,
                'title': title,
                'formats': formats,
                'description': description,
            }

        # Fallback to og:video if direct URLs not found
        og_video = self._og_search_video_url(webpage, default=None)
        if og_video:
            return {
                'id': video_id,
                'title': title,
                'url': og_video,
            }

        self.raise_no_formats('No playable video URLs found on the page', expected=True)
