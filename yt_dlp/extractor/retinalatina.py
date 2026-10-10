import hashlib
import json

from .common import InfoExtractor


class RetinaLatinaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?retinalatina\.org/peliculas/(?P<id>.+)/'
    _TESTS = [
        {
            'url': 'https://www.retinalatina.org/peliculas/whisky-pablo-stoll-juan-rebella/',
            'md5': '2f714bacc66d725072ab8b7c40ae278f',
            'info_dict': {
                'id': 'whisky-pablo-stoll-juan-rebella',
                'ext': 'mp4',
                'title': 'Whisky',
                'description': 'Whisky - La visita de un hermano rompe la rutina silenciosa de un hombre y revela tres formas distintas de estar solo',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        def_id = hashlib.md5(
            (
                'definition-config-vod-'
                + self._search_regex(
                    r'<iframe id="iframePlayerCustom" src="https://player.instantvideocloud.net/#/embed/[a-z0-9]+/([a-z0-9\-]+)"',
                    webpage,
                    'video_definition_id',
                    group=1,
                )
            ).encode(),
        ).hexdigest()

        video_definition = json.loads(
            self._download_webpage(
                f'https://json.instantvideocloud.net/definition/vod/videos/retina/{def_id}.json',
                video_id,
            ),
        )

        formats = self._extract_m3u8_formats(
            video_definition['srcMobile'],
            video_id,
            headers={
                'Referer': 'https://player.instantvideocloud.net/',
            },
        )
        for f in formats:
            f['http_headers'] = {
                'Referer': 'https://player.instantvideocloud.net/',
            }

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
        }
