from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_iso8601,
    traverse_obj,
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
        for key, value in state.items():
            # We can be given many different content objects, we want the one where the slug matches the video ID.
            if key.startswith('Content') and traverse_obj(value, ('slug')) == video_id:
                content_data = value
                break

        # If the user is not authenticated, and this video is not public, the content will be hidden. In this case show an error to the user.
        if content_data is None:
            raise ExtractorError('Failed to find content data. Either the given content is not a video, or it requires authentication', expected=True)
        if content_data['contentVideo'] is None:
            raise ExtractorError('Failed to find content video. Either the given content is not a video, or it requires authentication', expected=True)

        # Apollo GraphQL quirk, works with references. We grab the thumbnail reference so we
        thumbnail_ref = traverse_obj(content_data, ('thumbnail', '__ref'))
        image_data = None
        if thumbnail_ref is not None:
            image_data = traverse_obj(state, (thumbnail_ref))

        # Prefer landscape thumbnail
        thumbnail_url = traverse_obj(image_data, ('sizes', 'landscape', 'url'))
        # If not found, try for square thumbnail
        if thumbnail_url is None:
            thumbnail_url = traverse_obj(image_data, ('sizes', 'square', 'url'))
        # Otherwise, fall back to any other, if one exists
        if thumbnail_url is None:
            thumbnail_url = traverse_obj(image_data, ('sizes', ..., 'url'))

        video_data = traverse_obj(content_data, ('contentVideo', 'video'))
        m3u8_url = traverse_obj(video_data, 'video')

        if m3u8_url is None:
            raise ExtractorError('Failed to find video data', expected=True)

        # Beacon puts additional JSON in stringified form in the videoData. This data contains information about subtitles, and
        # as such we parse this, and extract these subtitles.
        additional_video_data_string = traverse_obj(video_data, 'videoData')
        additional_video_data = self._parse_json(additional_video_data_string, video_id)
        tracks_arr = traverse_obj(additional_video_data, ('playlist', ..., 'tracks'))
        subtitles = {}
        if tracks_arr is not None:
            for tracks in tracks_arr:
                for track in tracks:
                    if traverse_obj(track, 'kind') == 'captions':
                        file = track['file']
                        language = traverse_obj(track, 'language')
                        if language is None:
                            language = "en"
                        else:
                            language = language.lower()
                        subs = {language: [{'url': file}]}
                        self._merge_subtitles(subs, target=subtitles)

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
            'subtitles': subtitles,
        }
