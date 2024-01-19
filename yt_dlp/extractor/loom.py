from .common import InfoExtractor
from datetime import datetime
from yt_dlp.utils.traversal import traverse_obj


class LoomIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?loom\.com/share/(?P<id>[a-z0-9]+)'
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

    def fetch_loom_download_url(self, id):
        json = self._download_json(f"https://www.loom.com/api/campaigns/sessions/{id}/transcoded-url", video_id=id, data=b'')
        return json["url"]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json = self._search_json(start_pattern=r'window\.loomSSRVideo\s*=', string=webpage, name="Json from Loom Webpage", video_id=video_id)
        videourl = self.fetch_loom_download_url(video_id)
        ext = self._search_regex(r'([a-zA-Z0-9]+)(?=\?)', videourl, 'ext', fatal=False)

        date_string = json.get('createdAt')
        date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y%m%d")

        formats = []
        formats.append({
            'url': videourl,
            'width': traverse_obj(json, ('video_properties', 'width')),
            'height': traverse_obj(json, ('video_properties', 'height')),
            'ext': ext,
            'filesize': traverse_obj(json, ('video_properties', 'name')),
        })

        return {
            'id': video_id,
            'title': json.get('name'),
            'uploader': json.get('owner_full_name'),
            'upload_date': date,
            'formats': formats,
            # 'view_count': json["total_views"], # View Count is always changing so don't know how to test this.
            # TODO more properties (see yt_dlp/extractor/common.py)
        }
