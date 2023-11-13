from .common import InfoExtractor
from ..utils import (
    js_to_json,
    parse_duration,
    unescapeHTML,
)


class DRBonanzaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dr\.dk/bonanza/[^/]+/\d+/[^/]+/(?P<id>\d+)/(?P<display_id>[^/?#&]+)'
    _TEST = {
        'url': 'http://www.dr.dk/bonanza/serie/154/matador/40312/matador---0824-komme-fremmede-',
        'info_dict': {
            'id': '40312',
            'display_id': 'matador---0824-komme-fremmede-',
            'ext': 'mp4',
            'title': 'MATADOR - 08:24. "Komme fremmede".',
            'description': 'md5:77b4c1ac4d4c1b9d610ab4395212ff84',
            'thumbnail': r're:^https?://.*\.(?:gif|jpg)$',
            'duration': 4613,
        },
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id, display_id = mobj.group('id', 'display_id')

        webpage = self._download_webpage(url, display_id)

        info = self._parse_html5_media_entries(
            url, webpage, display_id, m3u8_id='hls',
            m3u8_entry_protocol='m3u8_native')[0]

        asset = self._parse_json(
            self._search_regex(
                r'(?s)currentAsset\s*=\s*({.+?})\s*</script', webpage, 'asset'),
            display_id, transform_source=js_to_json)

        title = unescapeHTML(asset['AssetTitle']).strip()

        def extract(field):
            return self._search_regex(
                r'<div[^>]+>\s*<p>%s:<p>\s*</div>\s*<div[^>]+>\s*<p>([^<]+)</p>' % field,
                webpage, field, default=None)

        info.update({
            'id': asset.get('AssetId') or video_id,
            'display_id': display_id,
            'title': title,
            'description': extract('Programinfo'),
            'duration': parse_duration(extract('Tid')),
            'thumbnail': asset.get('AssetImageUrl'),
        })
        return info
