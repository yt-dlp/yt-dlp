from .common import InfoExtractor
from ..utils import js_to_json


class OnionStudiosIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?onionstudios\.com/(?:video(?:s/[^/]+-|/)|embed\?.*\bid=)(?P<id>\d+)(?!-)'
    _EMBED_REGEX = [r'(?s)<(?:iframe|bulbs-video)[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?onionstudios\.com/(?:embed.+?|video/\d+\.json))\1']

    _TESTS = [{
        'url': 'http://www.onionstudios.com/videos/hannibal-charges-forward-stops-for-a-cocktail-2937',
        'md5': '5a118d466d62b5cd03647cf2c593977f',
        'info_dict': {
            'id': '3459881',
            'ext': 'mp4',
            'title': 'Hannibal charges forward, stops for a cocktail',
            'description': 'md5:545299bda6abf87e5ec666548c6a9448',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'a.v. club',
            'upload_date': '20150619',
            'timestamp': 1434728546,
        },
    }, {
        'url': 'http://www.onionstudios.com/embed?id=2855&autoplay=true',
        'only_matching': True,
    }, {
        'url': 'http://www.onionstudios.com/video/6139.json',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://onionstudios.com/embed/dc94dc2899fe644c0e7241fa04c1b732.js',
            video_id)
        mcp_id = str(self._parse_json(self._search_regex(
            r'window\.mcpMapping\s*=\s*({.+?});', webpage,
            'MCP Mapping'), video_id, js_to_json)[video_id]['mcp_id'])
        return self.url_result(
            'http://kinja.com/ajax/inset/iframe?id=mcp-' + mcp_id,
            'KinjaEmbed', mcp_id)
