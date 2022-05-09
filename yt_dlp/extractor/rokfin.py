import itertools
from datetime import datetime

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    float_or_none,
    format_field,
    int_or_none,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


_API_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/'


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

        metadata = self._download_json(f'{_API_BASE_URL}{video_id}', video_id)

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
            if traverse_obj(metadata, 'premiumPlan', 'premium'):
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
                needs_premium=bool(traverse_obj(metadata, 'premiumPlan', 'premium')),
                is_private=False, needs_subscription=False, needs_auth=False, is_unlisted=False),
            # 'comment_count': metadata.get('numComments'), # Data provided by website is wrong
            '__post_extractor': self.extract_comments(video_id) if video_type == 'post' else None,
        }

    def _get_comments(self, video_id):
        pages_total = None
        for page_n in itertools.count():
            raw_comments = self._download_json(
                f'{_API_BASE_URL}comment?postId={video_id[5:]}&page={page_n}&size=50',
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

            pages_total = int_or_none(raw_comments.get('totalPages')) or None
            is_last = raw_comments.get('last')
            if not raw_comments.get('content') or is_last or (page_n > pages_total if pages_total else is_last is not False):
                return


class RokfinPlaylistBaseIE(InfoExtractor):
    _TYPES = {
        'video': 'post',
        'audio': 'post',
        'stream': 'stream',
        'dead_stream': 'stream',
        'stack': 'stack',
    }

    def _get_video_data(self, metadata):
        for content in metadata.get('content') or []:
            media_type = self._TYPES.get(content.get('mediaType'))
            video_id = content.get('id') if media_type == 'post' else content.get('mediaId')
            if not media_type or not video_id:
                continue

            yield self.url_result(f'https://rokfin.com/{media_type}/{video_id}', video_id=f'{media_type}/{video_id}',
                                  video_title=str_or_none(traverse_obj(content, ('content', 'contentTitle'))))


class RokfinStackIE(RokfinPlaylistBaseIE):
    IE_NAME = 'rokfin:stack'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/stack/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.rokfin.com/stack/271/Tulsi-Gabbard-Portsmouth-Townhall-FULL--Feb-9-2020',
        'playlist_count': 8,
        'info_dict': {
            'id': '271',
        },
    }]

    def _real_extract(self, url):
        list_id = self._match_id(url)
        return self.playlist_result(self._get_video_data(
            self._download_json(f'{_API_BASE_URL}stack/{list_id}', list_id)), list_id)


class RokfinChannelIE(RokfinPlaylistBaseIE):
    IE_NAME = 'rokfin:channel'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?!((feed/?)|(discover/?)|(channels/?))$)(?P<id>[^/]+)/?$'
    _TESTS = [{
        'url': 'https://rokfin.com/TheConvoCouch',
        'playlist_mincount': 100,
        'info_dict': {
            'id': '12071-new',
            'title': 'TheConvoCouch - New',
            'description': 'md5:bb622b1bca100209b91cd685f7847f06',
        },
    }]

    _TABS = {
        'new': 'posts',
        'top': 'top',
        'videos': 'video',
        'podcasts': 'audio',
        'streams': 'stream',
        'stacks': 'stack',
    }

    def _real_initialize(self):
        self._validate_extractor_args()

    def _validate_extractor_args(self):
        requested_tabs = self._configuration_arg('tab', None)
        if requested_tabs is not None and (len(requested_tabs) > 1 or requested_tabs[0] not in self._TABS):
            raise ExtractorError(f'Invalid extractor-arg "tab". Must be one of {", ".join(self._TABS)}', expected=True)

    def _entries(self, channel_id, channel_name, tab):
        pages_total = None
        for page_n in itertools.count(0):
            if tab in ('posts', 'top'):
                data_url = f'{_API_BASE_URL}user/{channel_name}/{tab}?page={page_n}&size=50'
            else:
                data_url = f'{_API_BASE_URL}post/search/{tab}?page={page_n}&size=50&creator={channel_id}'
            metadata = self._download_json(
                data_url, channel_name,
                note=f'Downloading video metadata page {page_n + 1}{format_field(pages_total, template=" of %s")}')

            yield from self._get_video_data(metadata)
            pages_total = int_or_none(metadata.get('totalPages')) or None
            is_last = metadata.get('last')
            if is_last or (page_n > pages_total if pages_total else is_last is not False):
                return

    def _real_extract(self, url):
        channel_name = self._match_id(url)
        channel_info = self._download_json(f'{_API_BASE_URL}user/{channel_name}', channel_name)
        channel_id = channel_info['id']
        tab = self._configuration_arg('tab', default=['new'])[0]

        return self.playlist_result(
            self._entries(channel_id, channel_name, self._TABS[tab]),
            f'{channel_id}-{tab}', f'{channel_name} - {tab.title()}', str_or_none(channel_info.get('description')))
