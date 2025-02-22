from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_resolution,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class MaarivIE(InfoExtractor):
    IE_NAME = 'maariv.co.il'
    _VALID_URL = r'https?://player\.maariv\.co\.il/public/player\.html\?(?:[^#]+&)?media=(?P<id>\d+)'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc=[\'"](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://player.maariv.co.il/public/player.html?player=maariv-desktop&media=3611585',
        'info_dict': {
            'id': '3611585',
            'duration': 75,
            'ext': 'mp4',
            'upload_date': '20231009',
            'title': 'מבצע חרבות ברזל',
            'timestamp': 1696851301,
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.maariv.co.il/news/law/Article-1044008',
        'info_dict': {
            'id': '3611585',
            'duration': 75,
            'ext': 'mp4',
            'upload_date': '20231009',
            'title': 'מבצע חרבות ברזל',
            'timestamp': 1696851301,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            f'https://dal.walla.co.il/media/{video_id}?origin=player.maariv.co.il', video_id)['data']

        formats = []
        if hls_url := traverse_obj(data, ('video', 'url', {url_or_none})):
            formats.extend(self._extract_m3u8_formats(hls_url, video_id, m3u8_id='hls', fatal=False))

        for http_format in traverse_obj(data, ('video', 'stream_urls', ..., 'stream_url', {url_or_none})):
            formats.append({
                'url': http_format,
                'format_id': 'http',
                **parse_resolution(http_format),
            })

        return {
            'id': video_id,
            **traverse_obj(data, {
                'title': 'title',
                'duration': ('video', 'duration', {int_or_none}),
                'timestamp': ('upload_date', {unified_timestamp}),
            }),
            'formats': formats,
        }
