from .common import InfoExtractor
from ..utils import (
    js_to_json,
    merge_dicts,
)


class NewsyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?newsy\.com/stories/(?P<id>[^/?#$&]+)'

    _TESTS = [{
        'url': 'https://www.newsy.com/stories/nft-trend-leads-to-fraudulent-art-auctions/',
        'info_dict': {
            'id': '609d65125b086c24fb529312',
            'ext': 'mp4',
            'title': 'NFT Art Auctions Have A Piracy Problem',
            'description': 'md5:971e52ab8bc97e50305475cde8284c83',
            'display_id': 'nft-trend-leads-to-fraudulent-art-auctions',
            'timestamp': 1621339200,
            'duration': 339630,
            'thumbnail': 'https://cdn.newsy.com/images/videos/x/1620927824_xyrrP4.jpg',
            'upload_date': '20210518'
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        data_json = self._parse_json(self._html_search_regex(
            r'data-video-player\s?=\s?"({[^"]+})">', webpage, 'data'), display_id, js_to_json)
        ld_json = self._search_json_ld(webpage, display_id, fatal=False)

        formats, subtitles = [], {}
        if data_json.get('stream'):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(data_json['stream'], display_id)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        self._sort_formats(formats)
        return merge_dicts(ld_json, {
            'id': data_json['id'],
            'display_id': display_id,
            'title': data_json.get('headline'),
            'duration': data_json.get('duration'),
            'thumbnail': data_json.get('image'),
            'formats': formats,
            'subtitles': subtitles,
        })
