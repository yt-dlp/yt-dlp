from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601
from ..utils.traversal import traverse_obj


class LoomIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?loom\.com/share/(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'https://www.loom.com/share/43d05f362f734614a2e81b4694a3a523',
        'md5': '2b0d36e4999c39fabdb617188f21ea1e',
        'info_dict': {
            'id': '43d05f362f734614a2e81b4694a3a523',
            'ext': 'mp4',
            'title': 'A Ruler for Windows - 28 March 2022',
            'uploader': 'wILLIAM PIP',
            'upload_date': '20220328',
        }
    }, {
        'url': 'https://www.loom.com/share/c43a642f815f4378b6f80a889bb73d8d',
        'md5': '281c57772c6364c7a860fc222ea8d222',
        'info_dict': {
            'id': 'c43a642f815f4378b6f80a889bb73d8d',
            'ext': 'mp4',
            'title': 'Lilah Nielsen Intro Video',
            'uploader': 'Lilah Nielsen',
            'upload_date': '20200826',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        metadata = self._search_json(
            r'window\.loomSSRVideo\s*=', webpage, 'metadata', video_id, fatal=False)
        video_url = self._download_json(
            f'https://www.loom.com/api/campaigns/sessions/{video_id}/transcoded-url',
            video_id, 'Downloading video url',  data=b'')['url']

        return {
            'id': video_id,
            'url': video_url,
            **traverse_obj(metadata, {
                'title': ('name', {str}),
                'uploader': ('owner_full_name', {str}),
                'timestamp': ('createdAt', {parse_iso8601}),
                'view_count': ('total_views', {int_or_none}),
                'width': ('video_properties', 'width', {int_or_none}),
                'height': ('video_properties', 'height', {int_or_none}),
                'filesize': ('video_properties', 'byte_size', {int_or_none}),
            }),
        }
