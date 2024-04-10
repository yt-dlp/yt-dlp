from .common import InfoExtractor
from ..utils import (
    determine_ext,
    merge_dicts,
    unified_timestamp,
    url_or_none
)
from ..utils.traversal import traverse_obj


class GodResourceIE(InfoExtractor):
    _VALID_URL = r'https?://new\.godresource\.com/video/(?P<id>\w+)'
    _TESTS = [{
        # hls stream
        'url': 'https://new.godresource.com/video/A01mTKjyf6w',
        'info_dict': {
            'id': 'A01mTKjyf6w',
            'ext': 'mp4',
            'view_count': int,
            'timestamp': 1710978666,
            'channel_id': 5,
            'thumbnail': 'https://cdn-02.godresource.com/e42968ac-9e8b-4231-ab86-f4f9d775841f/thumbnail.jpg',
            'channel': 'Stedfast Baptist Church',
            'upload_date': '20240320',
            'title': 'GodResource',
        }
    }, {
        # mp4 link
        'url': 'https://new.godresource.com/video/01DXmBbQv_X',
        'info_dict': {
            'id': '01DXmBbQv_X',
            'ext': 'mp4',
            'channel_id': 12,
            'view_count': int,
            'timestamp': 1687996800,
            'thumbnail': 'https://cdn-02.godresource.com/sodomitedeception/thumbnail.jpg',
            'channel': 'Documentaries',
            'title': 'The Sodomite Deception',
            'upload_date': '20230629',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        # the website is oddly giving all request as 404 at first and then loaded with js
        webpage, _ = self._download_webpage_handle(url, display_id, expected_status=404)

        api_data = self._download_json(
            f'https://api.godresource.com/api/Streams/{display_id}', display_id)

        video_url = api_data['streamUrl']

        # TODO: better name?
        extraction_result = {}
        if determine_ext(video_url) == 'm3u8':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                api_data['streamUrl'], display_id)

            extraction_result = {
                'formats': formats,
                'subtitles': subtitles
            }
        elif determine_ext(video_url) == 'mp4':
            extraction_result = {
                'url': video_url,
                'ext': 'mp4'
            }

        return {
            'id': display_id,
            **extraction_result,
            'title': '',
            **traverse_obj(api_data, {
                'title': ('title', {str}),
                'thumbnail': ('thumbnail', {url_or_none}),
                'view_count': ('views', {int}),
                'channel': ('channelName', {str}),
                'channel_id': ('channelId', {str_or_none}),
                'timestamp': ('streamDateCreated', {unified_timestamp}),
                'modified_timestamp': ('streamDataModified', {unified_timestamp})
            })
        }
