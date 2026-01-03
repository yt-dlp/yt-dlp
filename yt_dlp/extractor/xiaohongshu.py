from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    js_to_json,
    url_or_none,
    urlhandle_detect_ext,
)
from ..utils.traversal import traverse_obj


class XiaoHongShuIE(InfoExtractor):
    _VALID_URL = r'https?://www\.xiaohongshu\.com/(?:explore|discovery/item)/(?P<id>[\da-f]+)'
    IE_DESC = '小红书'
    _LOGIN_HINT = 'Use --cookies-from-browser or --cookies with a logged-in browser session'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        initial_state = self._search_json(
            r'window\.__INITIAL_STATE__\s*=',
            webpage,
            'initial state',
            video_id,
            transform_source=js_to_json,
        )

        note = traverse_obj(
            initial_state,
            ('note', 'noteDetailMap', video_id, 'note'),
            expected_type=dict,
        )

        if not note:
            raise ExtractorError('Unable to locate note data')

        streams = traverse_obj(
            note,
            ('video', 'media', 'stream', ..., ...),
            expected_type=dict,
        ) or []

        formats = []
        for stream in streams:
            base = {
                'fps': int_or_none(stream.get('fps')),
                'width': int_or_none(stream.get('width')),
                'height': int_or_none(stream.get('height')),
                'vcodec': stream.get('videoCodec'),
                'acodec': stream.get('audioCodec'),
                'vbr': int_or_none(stream.get('videoBitrate'), scale=1000),
                'abr': int_or_none(stream.get('audioBitrate'), scale=1000),
                'tbr': int_or_none(stream.get('avgBitrate'), scale=1000),
                'filesize': int_or_none(stream.get('size')),
                'duration': float_or_none(stream.get('duration'), scale=1000),
                'format': stream.get('qualityType'),
            }

            for media_url in traverse_obj(
                stream,
                ('masterUrl', ('backupUrls', ...)),
                expected_type=url_or_none,
            ):
                formats.append({
                    'url': media_url,
                    **base,
                })

        # Original video (only available when authenticated)
        origin_key = traverse_obj(note, ('video', 'consumer', 'originVideoKey'), expected_type=str)
        if origin_key:
            urlh = self._request_webpage(
                f'https://sns-video-bd.xhscdn.com/{origin_key}',
                video_id,
                note='Checking original video availability',
                fatal=False,
            )
            if urlh:
                formats.append({
                    'format_id': 'direct',
                    'url': urlh.url,
                    'ext': urlhandle_detect_ext(urlh, default='mp4'),
                    'filesize': int_or_none(urlh.get_header('Content-Length')),
                    'quality': 1,
                })

        # Explicit stream gating detection
        if not formats:
            if traverse_obj(note, ('video', 'media')):
                self.raise_login_required(
                    'Xiaohongshu now requires a web_session cookie to access video streams',
                    metadata_available=True,
                )
            raise ExtractorError('No video formats found')

        thumbnails = []
        for img in traverse_obj(note, ('imageList', ...), expected_type=dict):
            for thumb_url in traverse_obj(img, ('urlDefault', 'urlPre'), expected_type=url_or_none):
                thumbnails.append({
                    'url': thumb_url,
                    'width': int_or_none(img.get('width')),
                    'height': int_or_none(img.get('height')),
                })

        return {
            'id': video_id,
            'formats': formats,
            'thumbnails': thumbnails,
            'title': self._html_search_meta('og:title', webpage, default=None),
            **traverse_obj(note, {
                'title': ('title', {str}),
                'description': ('desc', {str}),
                'tags': ('tagList', ..., 'name', {str}),
                'uploader_id': ('user', 'userId', {str}),
            }),
        }
