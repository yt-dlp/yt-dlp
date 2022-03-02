# coding: utf-8

import itertools
from datetime import datetime

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    format_field,
    int_or_none,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class RokfinIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?P<id>(?P<type>post|stream)/\d+)'
    _TESTS = [{
        'url': 'https://www.rokfin.com/post/57548/Mitt-Romneys-Crazy-Solution-To-Climate-Change',
        'info_dict': {
            'id': 'post/57548',
            'ext': 'mp4',
            'title': 'Mitt Romney\'s Crazy Solution To Climate Change',
            'thumbnail': r're:https://img\.production\.rokfin\.com/.+',
            'upload_date': '20211023',
            'timestamp': 1634998029,
            'channel': 'Jimmy Dore',
            'channel_id': 65429,
            'channel_url': 'https://rokfin.com/TheJimmyDoreShow',
            'duration': 213.0,
            'availability': 'public',
            'live_status': 'not_live',
            'dislike_count': int,
            'like_count': int,
        }
    }, {
        'url': 'https://rokfin.com/post/223/Julian-Assange-Arrested-Streaming-In-Real-Time',
        'info_dict': {
            'id': 'post/223',
            'ext': 'mp4',
            'title': 'Julian Assange Arrested: Streaming In Real Time',
            'thumbnail': r're:https://img\.production\.rokfin\.com/.+',
            'upload_date': '20190412',
            'timestamp': 1555052644,
            'channel': 'Ron Placone',
            'channel_id': 10,
            'channel_url': 'https://rokfin.com/RonPlacone',
            'availability': 'public',
            'live_status': 'not_live',
            'dislike_count': int,
            'like_count': int,
            'tags': ['FreeThinkingMedia^', 'RealProgressives^'],
        }
    }, {
        'url': 'https://www.rokfin.com/stream/10543/Its-A-Crazy-Mess-Regional-Director-Blows-Whistle-On-Pfizers-Vaccine-Trial-Data',
        'info_dict': {
            'id': 'stream/10543',
            'ext': 'mp4',
            'title': '"It\'s A Crazy Mess" Regional Director Blows Whistle On Pfizer\'s Vaccine Trial Data',
            'thumbnail': r're:https://img\.production\.rokfin\.com/.+',
            'description': 'md5:324ce2d3e3b62e659506409e458b9d8e',
            'channel': 'Ryan Cristián',
            'channel_id': 53856,
            'channel_url': 'https://rokfin.com/TLAVagabond',
            'availability': 'public',
            'is_live': False,
            'was_live': True,
            'live_status': 'was_live',
            'timestamp': 1635874720,
            'release_timestamp': 1635874720,
            'release_date': '20211102',
            'upload_date': '20211102',
            'dislike_count': int,
            'like_count': int,
            'tags': ['FreeThinkingMedia^'],
        }
    }]

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')

        metadata = self._download_json(f'https://prod-api-v2.production.rokfin.com/api/v2/public/{video_id}',
                                       video_id, fatal=False) or {}

        scheduled = unified_timestamp(metadata.get('scheduledAt'))
        live_status = ('was_live' if metadata.get('stoppedAt')
                       else 'is_upcoming' if scheduled
                       else 'is_live' if video_type == 'stream'
                       else 'not_live')

        video_url = traverse_obj(metadata, 'url', ('content', 'contentUrl'), expected_type=url_or_none)
        formats, subtitles = [{'url': video_url}] if video_url else [], {}
        if determine_ext(video_url) == 'm3u8':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                video_url, video_id, fatal=False, live=live_status == 'is_live')

        if not formats:
            if metadata.get('premiumPlan'):
                self.raise_login_required('This video is only available to premium users', True, method='cookies')
            elif scheduled:
                self.raise_no_formats(
                    f'Stream is offline; sheduled for {datetime.fromtimestamp(scheduled).strftime("%Y-%m-%d %H:%M:%S")}',
                    video_id=video_id, expected=True)
        self._sort_formats(formats)

        uploader = traverse_obj(metadata, ('createdBy', 'username'), ('creator', 'username'))
        timestamp = (scheduled or float_or_none(metadata.get('postedAtMilli'), 1000)
                     or unified_timestamp(metadata.get('creationDateTime')))
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': str_or_none(traverse_obj(metadata, 'title', ('content', 'contentTitle'))),
            'duration': float_or_none(traverse_obj(metadata, ('content', 'duration'))),
            'thumbnail': url_or_none(traverse_obj(metadata, 'thumbnail', ('content', 'thumbnailUrl1'))),
            'description': str_or_none(traverse_obj(metadata, 'description', ('content', 'contentDescription'))),
            'like_count': int_or_none(metadata.get('likeCount')),
            'dislike_count': int_or_none(metadata.get('dislikeCount')),
            'channel': str_or_none(traverse_obj(metadata, ('createdBy', 'name'), ('creator', 'name'))),
            'channel_id': traverse_obj(metadata, ('createdBy', 'id'), ('creator', 'id')),
            'channel_url': url_or_none(f'https://rokfin.com/{uploader}') if uploader else None,
            'timestamp': timestamp,
            'release_timestamp': timestamp if live_status != 'not_live' else None,
            'tags': traverse_obj(metadata, ('tags', ..., 'title'), expected_type=str_or_none),
            'live_status': live_status,
            'availability': self._availability(
                needs_premium=bool(metadata.get('premiumPlan')),
                is_private=False, needs_subscription=False, needs_auth=False, is_unlisted=False),
            # 'comment_count': metadata.get('numComments'), # Data provided by website is wrong
            '__post_extractor': self.extract_comments(video_id) if video_type == 'post' else None,
        }

    def _get_comments(self, video_id):
        pages_total = None
        for page_n in itertools.count():
            raw_comments = self._download_json(
                f'https://prod-api-v2.production.rokfin.com/api/v2/public/comment?postId={video_id[5:]}&page={page_n}&size=50',
                video_id, note=f'Downloading viewer comments page {page_n + 1}{format_field(pages_total, template=" of %s")}',
                fatal=False) or {}

            for comment in raw_comments.get('content') or []:
                yield {
                    'text': str_or_none(comment.get('comment')),
                    'author': str_or_none(comment.get('name')),
                    'id': comment.get('commentId'),
                    'author_id': comment.get('userId'),
                    'parent': 'root',
                    'like_count': int_or_none(comment.get('numLikes')),
                    'dislike_count': int_or_none(comment.get('numDislikes')),
                    'timestamp': unified_timestamp(comment.get('postedAt'))
                }

            pages_total = int_or_none(raw_comments.get('totalPages'))
            if not raw_comments.get('content') or raw_comments.get('last') is not False or page_n > (pages_total or 0):
                return
