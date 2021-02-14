from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    int_or_none,
    ExtractorError,
)


class VubeIE(InfoExtractor):
    IE_NAME = 'vube'
    IE_DESC = 'Vube.com'
    _VALID_URL = r'https?://vube\.com/(?:[^/]+/)+(?P<id>[\da-zA-Z]{10})\b'

    _TESTS = [
        {
            'url': 'http://vube.com/trending/William+Wei/Y8NUZ69Tf7?t=s',
            'md5': 'e7aabe1f8f1aa826b9e4735e1f9cee42',
            'info_dict': {
                'id': 'Y8NUZ69Tf7',
                'ext': 'mp4',
                'title': 'Best Drummer Ever [HD]',
                'description': 'md5:2d63c4b277b85c2277761c2cf7337d71',
                'thumbnail': r're:^https?://.*\.jpg',
                'uploader': 'William',
                'timestamp': 1406876915,
                'upload_date': '20140801',
                'duration': 258.051,
                'like_count': int,
                'dislike_count': int,
                'comment_count': int,
                'categories': ['amazing', 'hd', 'best drummer ever', 'william wei', 'bucket drumming', 'street drummer', 'epic street drumming'],
            },
            'skip': 'Not accessible from Travis CI server',
        }, {
            'url': 'http://vube.com/Chiara+Grispo+Video+Channel/YL2qNPkqon',
            'md5': 'db7aba89d4603dadd627e9d1973946fe',
            'info_dict': {
                'id': 'YL2qNPkqon',
                'ext': 'mp4',
                'title': 'Chiara Grispo - Price Tag by Jessie J',
                'description': 'md5:8ea652a1f36818352428cb5134933313',
                'thumbnail': r're:^http://frame\.thestaticvube\.com/snap/[0-9x]+/102e7e63057-5ebc-4f5c-4065-6ce4ebde131f\.jpg$',
                'uploader': 'Chiara.Grispo',
                'timestamp': 1388743358,
                'upload_date': '20140103',
                'duration': 170.56,
                'like_count': int,
                'dislike_count': int,
                'comment_count': int,
                'categories': ['pop', 'music', 'cover', 'singing', 'jessie j', 'price tag', 'chiara grispo'],
            },
            'skip': 'Removed due to DMCA',
        },
        {
            'url': 'http://vube.com/SerainaMusic/my-7-year-old-sister-and-i-singing-alive-by-krewella/UeBhTudbfS?t=s&n=1',
            'md5': '5d4a52492d76f72712117ce6b0d98d08',
            'info_dict': {
                'id': 'UeBhTudbfS',
                'ext': 'mp4',
                'title': 'My 7 year old Sister and I singing "Alive" by Krewella',
                'description': 'md5:40bcacb97796339f1690642c21d56f4a',
                'thumbnail': r're:^http://frame\.thestaticvube\.com/snap/[0-9x]+/102265d5a9f-0f17-4f6b-5753-adf08484ee1e\.jpg$',
                'uploader': 'Seraina',
                'timestamp': 1396492438,
                'upload_date': '20140403',
                'duration': 240.107,
                'like_count': int,
                'dislike_count': int,
                'comment_count': int,
                'categories': ['seraina', 'jessica', 'krewella', 'alive'],
            },
            'skip': 'Removed due to DMCA',
        }, {
            'url': 'http://vube.com/vote/Siren+Gene/0nmsMY5vEq?n=2&t=s',
            'md5': '0584fc13b50f887127d9d1007589d27f',
            'info_dict': {
                'id': '0nmsMY5vEq',
                'ext': 'mp4',
                'title': 'Frozen - Let It Go Cover by Siren Gene',
                'description': 'My rendition of "Let It Go" originally sung by Idina Menzel.',
                'thumbnail': r're:^http://frame\.thestaticvube\.com/snap/[0-9x]+/10283ab622a-86c9-4681-51f2-30d1f65774af\.jpg$',
                'uploader': 'Siren',
                'timestamp': 1395448018,
                'upload_date': '20140322',
                'duration': 221.788,
                'like_count': int,
                'dislike_count': int,
                'comment_count': int,
                'categories': ['let it go', 'cover', 'idina menzel', 'frozen', 'singing', 'disney', 'siren gene'],
            },
            'skip': 'Removed due to DMCA',
        }
    ]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')

        video = self._download_json(
            'http://vube.com/t-api/v1/video/%s' % video_id, video_id, 'Downloading video JSON')

        public_id = video['public_id']

        formats = []

        for media in video['media'].get('video', []) + video['media'].get('audio', []):
            if media['transcoding_status'] != 'processed':
                continue
            fmt = {
                'url': 'http://video.thestaticvube.com/video/%s/%s.mp4' % (media['media_resolution_id'], public_id),
                'abr': int(media['audio_bitrate']),
                'format_id': compat_str(media['media_resolution_id']),
            }
            vbr = int(media['video_bitrate'])
            if vbr:
                fmt.update({
                    'vbr': vbr,
                    'height': int(media['height']),
                })
            formats.append(fmt)

        self._sort_formats(formats)

        if not formats and video.get('vst') == 'dmca':
            raise ExtractorError(
                'This video has been removed in response to a complaint received under the US Digital Millennium Copyright Act.',
                expected=True)

        title = video['title']
        description = video.get('description')
        thumbnail = self._proto_relative_url(video.get('thumbnail_src'), scheme='http:')
        uploader = video.get('user_alias') or video.get('channel')
        timestamp = int_or_none(video.get('upload_time'))
        duration = video['duration']
        view_count = video.get('raw_view_count')
        like_count = video.get('total_likes')
        dislike_count = video.get('total_hates')

        comments = video.get('comments')
        comment_count = None
        if comments is None:
            comment_data = self._download_json(
                'http://vube.com/api/video/%s/comment' % video_id,
                video_id, 'Downloading video comment JSON', fatal=False)
            if comment_data is not None:
                comment_count = int_or_none(comment_data.get('total'))
        else:
            comment_count = len(comments)

        categories = [tag['text'] for tag in video['tags']]

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'timestamp': timestamp,
            'duration': duration,
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'comment_count': comment_count,
            'categories': categories,
        }
