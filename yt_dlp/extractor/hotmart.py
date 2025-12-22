import json

from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class HotmartEmbedIE(InfoExtractor):
    IE_NAME = 'hotmart:embed'
    IE_DESC = 'Hotmart embedded player'
    _VALID_URL = r'https?://player\.hotmart\.com/embed/(?P<id>[A-Za-z0-9_-]+)'

    _TESTS = [{
        'url': 'https://player.hotmart.com/embed/DZwydedYq3?signature=XVfBT5_WSEhdVA6SAEoRqMiqcqVL8CuVBaNC2ZZoIS1mJ1UQ3hvemsy-fM2txWU1dU9X6Neg2P9sbuKJK5Bj4eahqs2r2oMWP66oqD3Ud7SJVGhwf80LMJ9WHiSCrB4mqOCSQB03_Hm8I8UHt6N3UbUwnUX-ZKqXZp4tI-1XD8weHfYour7_Oy1Oa_PvryNj7JV8al5rnmbGAauAIcEXFfCGKbob7lSUe0Ca2mtcekUU0PiMbYCks75YLE4BaJMCbC63FxKaG_HJGrX1fnPFsVbSrwYGMxtxN-7Cw4_UrryEuM1JsBLj62yUUJMwySHxRGzz4pMmja0wJ0TooJOsCg%3D%3D&token=aa2d356b-e2f0-45e8-9725-e0efc7b5d29c&user=125483999&autoplay=autoplay',
        'info_dict': {
            'id': 'DZwydedYq3',
            'ext': 'mp4',
            'thumbnail': r're:https?://.*\.jpeg',
            'duration': int,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            url, video_id, note='Downloading Hotmart embed page'
        )

        next_data = self._search_regex(
            r'<script[^>]+id="__NEXT_DATA__"[^>]*>(?P<json>{.+?})</script>',
            webpage,
            'NEXT_DATA',
            group='json'
        )

        data = json.loads(next_data)

        app_data = traverse_obj(
            data, ('props', 'pageProps', 'applicationData')
        )
        if not app_data:
            raise ExtractorError('Unable to find applicationData')

        media_assets = traverse_obj(app_data, ('mediaAssets',))
        if not media_assets:
            raise ExtractorError('No mediaAssets found')

        m3u8_url = traverse_obj(media_assets, (0, 'url'))
        if not m3u8_url:
            raise ExtractorError('No HLS URL found')

        formats = self._extract_m3u8_formats(
            m3u8_url,
            video_id,
            ext='mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls',
            headers={
                'Referer': 'https://player.hotmart.com/',
                'Origin': 'https://player.hotmart.com',
            },
            fatal=True,
        )

        for f in formats:
            f.setdefault('http_headers', {})
            f['http_headers'].update({
                'Referer': 'https://player.hotmart.com/',
                'Origin': 'https://player.hotmart.com',
            })

        return {
            'id': video_id,
            'title': app_data.get('mediaTitle') or video_id,
            'thumbnail': app_data.get('thumbnailUrl'),
            'duration': app_data.get('mediaDuration'),
            'formats': formats,
        }
