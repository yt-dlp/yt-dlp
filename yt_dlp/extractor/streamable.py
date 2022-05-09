import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    try_get,
    parse_codecs,
)


class StreamableIE(InfoExtractor):
    _VALID_URL = r'https?://streamable\.com/(?:[es]/)?(?P<id>\w+)'
    _TESTS = [
        {
            'url': 'https://streamable.com/dnd1',
            'md5': '3e3bc5ca088b48c2d436529b64397fef',
            'info_dict': {
                'id': 'dnd1',
                'ext': 'mp4',
                'title': 'Mikel Oiarzabal scores to make it 0-3 for La Real against Espanyol',
                'thumbnail': r're:https?://.*\.jpg$',
                'uploader': 'teabaker',
                'timestamp': 1454964157.35115,
                'upload_date': '20160208',
                'duration': 61.516,
                'view_count': int,
            }
        },
        # older video without bitrate, width/height, codecs, etc. info
        {
            'url': 'https://streamable.com/moo',
            'md5': '2cf6923639b87fba3279ad0df3a64e73',
            'info_dict': {
                'id': 'moo',
                'ext': 'mp4',
                'title': '"Please don\'t eat me!"',
                'thumbnail': r're:https?://.*\.jpg$',
                'timestamp': 1426115495,
                'upload_date': '20150311',
                'duration': 12,
                'view_count': int,
            }
        },
        {
            'url': 'https://streamable.com/e/dnd1',
            'only_matching': True,
        },
        {
            'url': 'https://streamable.com/s/okkqk/drxjds',
            'only_matching': True,
        }
    ]

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+src=(?P<q1>[\'"])(?P<src>(?:https?:)?//streamable\.com/(?:(?!\1).+))(?P=q1)',
            webpage)
        if mobj:
            return mobj.group('src')

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Note: Using the ajax API, as the public Streamable API doesn't seem
        # to return video info like the title properly sometimes, and doesn't
        # include info like the video duration
        video = self._download_json(
            'https://ajax.streamable.com/videos/%s' % video_id, video_id)

        # Format IDs:
        # 0 The video is being uploaded
        # 1 The video is being processed
        # 2 The video has at least one file ready
        # 3 The video is unavailable due to an error
        status = video.get('status')
        if status != 2:
            raise ExtractorError(
                'This video is currently unavailable. It may still be uploading or processing.',
                expected=True)

        title = video.get('reddit_title') or video['title']

        formats = []
        for key, info in video['files'].items():
            if not info.get('url'):
                continue
            formats.append({
                'format_id': key,
                'url': self._proto_relative_url(info['url']),
                'width': int_or_none(info.get('width')),
                'height': int_or_none(info.get('height')),
                'filesize': int_or_none(info.get('size')),
                'fps': int_or_none(info.get('framerate')),
                'vbr': float_or_none(info.get('bitrate'), 1000),
                'vcodec': parse_codecs(try_get(info, lambda x: x['input_metadata']['video_codec_name'])).get('vcodec'),
                'acodec': parse_codecs(try_get(info, lambda x: x['input_metadata']['audio_codec_name'])).get('acodec'),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': video.get('description'),
            'thumbnail': self._proto_relative_url(video.get('thumbnail_url')),
            'uploader': video.get('owner', {}).get('user_name'),
            'timestamp': float_or_none(video.get('date_added')),
            'duration': float_or_none(video.get('duration')),
            'view_count': int_or_none(video.get('plays')),
            'formats': formats
        }
