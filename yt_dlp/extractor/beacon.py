from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    traverse_obj,
    ExtractorError,
)


class BeaconTvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?beacon\.tv/content/(?P<id>.+)'

    _TESTS = [{
        'url': 'https://beacon.tv/content/welcome-to-beacon',
        'md5': 'b3f5932d437f288e662f10f3bfc5bd04',
        'info_dict': {
            'id': 'welcome-to-beacon',
            'ext': 'mp4',
            'upload_date': '20240509',
            'description': 'md5:ea2bd32e71acf3f9fca6937412cc3563',
            'thumbnail': 'https://imagedelivery.net/_18WuG-hYMyVquF6KgU_xQ/critrole-beacon-staging-backend/beacon_trailer_thumbnail_beacon_website-5-600x600.png/format=auto',
            'title': 'Your home for Critical Role!',
            'timestamp': 1715227200,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_data_string = self._html_search_regex(r'<script id="__NEXT_DATA__" type="application/json">(.+)</script>', webpage, 'JSON Body')
        json_data = self._parse_json(json_data_string, video_id)

        state = traverse_obj(json_data, ('props', 'pageProps', '__APOLLO_STATE__'))

        content_data = None
        image_data = None
        for key, value in state.items():
            if key.startswith('Content'):
                content_data = value
            if key.startswith('Image'):
                image_data = value

        if content_data is None:
            raise ExtractorError('Failed to find content data', expected=True)
        if content_data['contentVideo'] is None:
            raise ExtractorError('Failed to find content video. Either the given content is not a video, or it requires authentication', expected=True)

        m3u8_url = traverse_obj(content_data, ('contentVideo', 'video', 'video'))

        if m3u8_url is None:
            raise ExtractorError('Failed to find video data', expected=True)

        thumbnail_url = traverse_obj(image_data, ('sizes', 'landscape', 'url'))
        if thumbnail_url is None:
            thumbnail_url = traverse_obj(image_data, ('sizes', 'square', 'url'))

        title = traverse_obj(content_data, 'title')
        description = traverse_obj(content_data, 'description')
        publishedAt = traverse_obj(content_data, 'publishedAt')

        formats = self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4')
        return {
            'id': video_id,
            'ext': 'mp4',
            'title': title,
            'formats': formats,
            'timestamp': parse_iso8601(publishedAt),
            'description': description,
            'thumbnail': thumbnail_url,
        }
