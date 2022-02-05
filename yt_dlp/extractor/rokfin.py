# coding: utf-8
from json import dumps
from math import ceil
import itertools
import datetime
from re import finditer
from urllib.parse import urlparse
from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    unified_timestamp,
    try_get,
    traverse_obj,
    int_or_none,
    bool_or_none,
    float_or_none,
    str_or_none,
    url_or_none,
    ExtractorError,
)


class RokfinIE(InfoExtractor):
    _NETRC_MACHINE = 'rokfin'


class RokfinSingleVideoIE(RokfinIE):
    _META_DATA_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/'
    _RECOMMENDED_VIDEO_BASE_URL = 'https://rokfin.com/'
    _CHANNEL_BASE_URL = 'https://rokfin.com/'


class RokfinPostIE(RokfinSingleVideoIE):
    IE_NAME = 'rokfin:post'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?P<id>post/[^/]+)'
    _TESTS = [{
        'url': 'https://www.rokfin.com/post/57548/Mitt-Romneys-Crazy-Solution-To-Climate-Change',
        'info_dict': {
            'id': 'post/57548',
            'ext': 'mp4',
            'title': 'Mitt Romney\'s Crazy Solution To Climate Change',
            'thumbnail': 're:https://img.production.rokfin.com/.+',
            'upload_date': '20211023',
            'timestamp': 1634998029,
            'creator': 'Jimmy Dore',
            'channel': 'Jimmy Dore',
            'channel_id': 65429,
            'channel_url': 'https://rokfin.com/TheJimmyDoreShow',
            'duration': 213.0,
            'availability': 'public',
            'live_status': 'not_live'
        }
    }]

    def _real_extract(self, url_from_user):
        if self.get_param('username') or self.get_param('password'):
            self.report_warning('site logins are unsupported')

        video_id = self._match_id(url_from_user)
        downloaded_json_meta_data = self._download_json(self._META_DATA_BASE_URL + video_id, video_id, fatal=False) or {}
        video_formats_url = url_or_none(traverse_obj(downloaded_json_meta_data, ('content', 'contentUrl')))
        availability = self._availability(
            is_private=False,
            needs_premium=True if downloaded_json_meta_data.get('premiumPlan') == 1 else False if downloaded_json_meta_data.get('premiumPlan') == 0 else None,
            # premiumPlan = 0 - no-premium content
            # premiumPlan = 1 - premium-only content
            needs_subscription=False,
            needs_auth=False,
            is_unlisted=False)

        if downloaded_json_meta_data.get('premiumPlan') not in (0, 1, None):
            self.report_warning(f'unknown availability code: {downloaded_json_meta_data.get("premiumPlan")}. Rokfin extractor should be updated')

        if video_formats_url:
            if try_get(video_formats_url, lambda x: urlparse(x).path.endswith('.m3u8')):
                frmts, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url=video_formats_url, video_id=video_id, fatal=False)
            else:
                frmts = [{'url': video_formats_url}]
                subs = None
        else:
            frmts = None
            subs = None

        if not frmts:
            if availability == 'premium_only':
                self.raise_no_formats(msg='premium content', video_id=video_id, expected=True)
            elif video_formats_url:
                self.raise_no_formats(msg='unable to download: missing meta data', video_id=video_id, expected=True)
            else:
                # We don't know why there is no (valid) meta data present.
                self.raise_no_formats(msg='unable to download', video_id=video_id, expected=True)

        self._sort_formats(frmts)
        return {
            'id': video_id,
            'title': str_or_none(traverse_obj(downloaded_json_meta_data, ('content', 'contentTitle'))),
            'webpage_url': self._RECOMMENDED_VIDEO_BASE_URL + video_id,
            # webpage_url = url_from_user minus the final part. The final part exists solely for human consumption and is otherwise irrelevant.
            'live_status': 'not_live',
            'duration': float_or_none(traverse_obj(downloaded_json_meta_data, ('content', 'duration'))),
            'thumbnail': url_or_none(traverse_obj(downloaded_json_meta_data, ('content', 'thumbnailUrl1'))),
            'description': str_or_none(traverse_obj(downloaded_json_meta_data, ('content', 'contentDescription'))),
            'like_count': int_or_none(downloaded_json_meta_data.get('likeCount')),
            'dislike_count': int_or_none(downloaded_json_meta_data.get('dislikeCount')),
            # 'comment_count': downloaded_json_meta_data.get('numComments'), # Uncomment when Rf corrects 'numComments' field.
            'availability': availability,
            'creator': str_or_none(traverse_obj(downloaded_json_meta_data, ('createdBy', 'name'))),
            'channel_id': traverse_obj(downloaded_json_meta_data, ('createdBy', 'id')),
            'channel': str_or_none(traverse_obj(downloaded_json_meta_data, ('createdBy', 'name'))),
            'channel_url': try_get(downloaded_json_meta_data, lambda x: url_or_none(self._CHANNEL_BASE_URL + x['createdBy']['username'])),
            'timestamp': unified_timestamp(downloaded_json_meta_data.get('creationDateTime')),
            'tags': downloaded_json_meta_data.get('tags') or [],
            'formats': frmts or [],
            'subtitles': subs or {},
            '__post_extractor': self.extract_comments(video_id=video_id)
        }

    def _get_comments(self, video_id):
        _COMMENTS_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/comment'
        _COMMENTS_PER_REQUEST = 50  # 50 is the maximum Rokfin permits per request.

        def dnl_comments_incrementally(base_url, video_id, comments_per_page):
            pages_total = None

            for page_n in itertools.count(0):
                raw_comments = self._download_json(
                    f'{base_url}?postId={video_id[5:]}&page={page_n}&size={comments_per_page}',
                    video_id,
                    note=f'Downloading viewer comments (page {page_n + 1}' + (f' of {pages_total}' if pages_total else '') + ')',
                    fatal=False) or {}

                raw_comments = raw_comments.get
                comments = raw_comments('content')
                pages_total = int_or_none(raw_comments('totalPages'))
                is_last_page = bool_or_none(raw_comments('last'))
                max_page_count_reached = None if pages_total is None else (page_n + 1 >= pages_total)

                if comments:
                    yield comments

                if is_last_page or max_page_count_reached or ((is_last_page is None) and (max_page_count_reached is None)) or not(comments):
                    return
                # The last two conditions are safety checks.

        for page_of_comments in dnl_comments_incrementally(_COMMENTS_BASE_URL, video_id, _COMMENTS_PER_REQUEST):
            for comment in page_of_comments:
                comment_text = str_or_none(comment.get('comment'))

                if comment_text is None:
                    continue

                yield {
                    'text': comment_text,
                    'author': str_or_none(comment.get('name')),
                    'id': comment.get('commentId'),
                    'author_id': comment.get('userId'),
                    'parent': 'root',
                    'like_count': int_or_none(comment.get('numLikes')),
                    'dislike_count': int_or_none(comment.get('numDislikes')),
                    'timestamp': unified_timestamp(comment.get('postedAt'))
                }


class RokfinStreamIE(RokfinSingleVideoIE):
    IE_NAME = 'rokfin:stream'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?P<id>stream/[^/]+)'
    _TESTS = [{
        'url': 'https://www.rokfin.com/stream/10543/Its-A-Crazy-Mess-Regional-Director-Blows-Whistle-On-Pfizers-Vaccine-Trial-Data',
        'info_dict': {
            'id': 'stream/10543',
            'ext': 'mp4',
            'title': '"It\'s A Crazy Mess" Regional Director Blows Whistle On Pfizer\'s Vaccine Trial Data',
            'thumbnail': 'https://img.production.rokfin.com/eyJidWNrZXQiOiJya2ZuLXByb2R1Y3Rpb24tbWVkaWEiLCJrZXkiOiIvdXNlci81Mzg1Ni9wb3N0L2Y0ZWY4YzQyLTdiMmYtNGZhYy05MDIzLTg4YmI5ZTNjY2ZiNi90aHVtYm5haWwvMDU4NjE1MTktNjE5NS00NTY4LWI4ZDAtNTdhZGUxMmZiZDcyIiwiZWRpdHMiOnsicmVzaXplIjp7IndpZHRoIjo2MDAsImhlaWdodCI6MzM3LCJmaXQiOiJjb3ZlciJ9fX0=',
            'uploader_id': 53856,
            'description': 'md5:324ce2d3e3b62e659506409e458b9d8e',
            'creator': 'Ryan Cristián',
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
            'upload_date': '20211102'
        }
    }]

    def _real_extract(self, url_from_user):
        if self.get_param('username') or self.get_param('password'):
            self.report_warning('site logins are unsupported')

        if self.get_param('live_from_start'):
            self.report_warning('--live-from-start is unsupported')

        video_id = self._match_id(url_from_user)
        downloaded_json_meta_data = self._download_json(self._META_DATA_BASE_URL + video_id, video_id, fatal=False) or {}
        availability = self._availability(
            needs_premium=bool(downloaded_json_meta_data.get('premium')) if downloaded_json_meta_data.get('premium') in (True, False, 0, 1) else None,
            is_private=False,
            needs_subscription=False,
            needs_auth=False,
            is_unlisted=False)
        m3u8_url = url_or_none(downloaded_json_meta_data.get('url'))
        stream_scheduled_for = try_get(downloaded_json_meta_data, lambda x: datetime.datetime.strptime(x.get('scheduledAt'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc))
        # 'scheduledAt' gets set to None after the stream becomes live.
        stream_ended_at = try_get(
            downloaded_json_meta_data,
            lambda x: datetime.datetime.strptime(
                x.get('stoppedAt'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc))
        # 'stoppedAt' is null unless the stream is finished. 'stoppedAt' likely contains an incorrect value,
        # so what matters to us is whether or not this field is *present*.

        if m3u8_url:
            frmts, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url=m3u8_url, video_id=video_id, fatal=False, live=(stream_scheduled_for is None and stream_ended_at is None))
        else:
            frmts = None
            subs = None

        if not frmts:
            if stream_scheduled_for:
                # The stream is pending.
                def error_message(stream_scheduled_for, availability):
                    time_diff = (stream_scheduled_for - datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)) if stream_scheduled_for >= datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) else (datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - stream_scheduled_for)
                    main_part = (f'{time_diff.days}D+' if time_diff.days else '') + f'{(time_diff.seconds // 3600):02}:{((time_diff.seconds % 3600) // 60):02}:{((time_diff.seconds % 3600) % 60):02}'

                    if stream_scheduled_for >= datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc):
                        return 'live in ' + main_part + (' (premium-only)' if availability == 'premium_only' else '') + '. Try --wait-for-video'
                    else:
                        return 'not live; ' + main_part + ' behind schedule' + (' (premium-only)' if availability == 'premium_only' else '') + '. Try --wait-for-video'
                self.raise_no_formats(error_message(stream_scheduled_for, availability), video_id=video_id, expected=True)
            elif availability == 'premium_only':
                self.raise_no_formats(msg='premium content', video_id=video_id, expected=True)
            elif m3u8_url:
                self.raise_no_formats(msg='unable to download: missing meta data', video_id=video_id, expected=True)
            else:
                # We don't know why there is no (valid) meta data present.
                self.raise_no_formats(msg='unable to download', video_id=video_id, expected=True)

            # --wait-for-video causes raise_no_formats(... expected=True ...) to print a warning message
            # and exit without raising ExtractorError.

        # 'postedAtMilli' shows when the stream (live or pending) appeared on Rokfin. As soon as the pending stream goes live,
        # the value of 'postedAtMilli' changes to reflect the stream's starting time.
        stream_started_at_timestamp = try_get(downloaded_json_meta_data, lambda x: x.get('postedAtMilli') / 1000) if stream_scheduled_for is None else None
        stream_started_at = try_get(stream_started_at_timestamp, lambda x: datetime.datetime.utcfromtimestamp(x).replace(tzinfo=datetime.timezone.utc))
        # The stream's actual (if live or finished) or announced (if pending) starting time:
        release_timestamp = try_get(stream_scheduled_for, lambda x: unified_timestamp(datetime.datetime.strftime(x, '%Y-%m-%dT%H:%M:%S'))) or stream_started_at_timestamp

        self._sort_formats(frmts)
        return {
            'id': video_id,
            'title': str_or_none(downloaded_json_meta_data.get('title')),
            'webpage_url': self._RECOMMENDED_VIDEO_BASE_URL + video_id,
            # webpage_url = url_from_user minus the final part. The final part exists solely for human consumption and is otherwise irrelevant.
            'manifest_url': m3u8_url,
            'thumbnail': url_or_none(downloaded_json_meta_data.get('thumbnail')),
            'description': str_or_none(downloaded_json_meta_data.get('description')),
            'like_count': int_or_none(downloaded_json_meta_data.get('likeCount')),
            'dislike_count': int_or_none(downloaded_json_meta_data.get('dislikeCount')),
            'creator': str_or_none(traverse_obj(downloaded_json_meta_data, ('creator', 'name'))),
            'channel': str_or_none(traverse_obj(downloaded_json_meta_data, ('creator', 'name'))),
            'channel_id': traverse_obj(downloaded_json_meta_data, ('creator', 'id')),
            'uploader_id': traverse_obj(downloaded_json_meta_data, ('creator', 'id')),
            'channel_url': try_get(downloaded_json_meta_data, lambda x: url_or_none(self._CHANNEL_BASE_URL + traverse_obj(x, ('creator', 'username')))),
            'availability': availability,
            'tags': downloaded_json_meta_data.get('tags') or [],
            'live_status': 'was_live' if (stream_scheduled_for is None) and (stream_ended_at is not None) else
                           'is_live' if stream_scheduled_for is None else  # stream_scheduled_for=stream_ended_at=None
                           'is_upcoming' if stream_ended_at is None else   # stream_scheduled_for is not None
                           None,  # Both stream_scheduled_for and stream_ended_at are not None: inconsistent meta data.
            # Remove the 'False and' part when Rokfin corrects the 'stoppedAt' field:
            'duration': (stream_ended_at - stream_started_at).total_seconds() if False and stream_started_at and stream_ended_at else None,
            'timestamp': release_timestamp,
            'release_timestamp': release_timestamp,
            'formats': frmts or [],
            'subtitles': subs or {},
            '__post_extractor': self.extract_comments(video_id=video_id)
        }

    def _get_comments(self, video_id):
        raise ExtractorError(msg='downloading stream chat is unsupported', expected=True)


class RokfinPlaylistIE(RokfinIE):
    def _get_video_data(self, json_data, video_base_url):
        def real_get_video_data(content):
            media_type = content.get('mediaType')
            fn = try_get(media_type, lambda y: {
                'video': lambda x: {'id': x['id'], 'url': f'{video_base_url}post/{x["id"]}'},
                'audio': lambda x: {'id': x['id'], 'url': f'{video_base_url}post/{x["id"]}'},
                'stream': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}stream/{x["mediaId"]}'},
                'dead_stream': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}stream/{x["mediaId"]}'},
                'stack': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}stack/{x["mediaId"]}'},
                'article': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}article/{x["mediaId"]}'},
                'ranking': lambda x: {'id': x['mediaId'], 'url': f'{video_base_url}ranking/{x["mediaId"]}'}
            }[y])

            if fn is None:
                self.to_screen('non-downloadable content skipped' + ('' if self.get_param('verbose') else '. Use --verbose for details'))
                self.write_debug(f'unprocessed entry: {content}')
                return

            video_data = try_get(content, fn)
            if video_data is None:
                self.write_debug(f'{media_type}: could not process content entry: {content}')
                return

            video_data['url'] = url_or_none(video_data.get('url'))

            if video_data.get('url') is None:
                self.to_screen('entry with missing or malformed URL skipped' + ('' if self.get_param('verbose') else '. Use --verbose for details'))
                self.write_debug(f'{media_type}: could not process content entry: {content}')
                return

            video_data['title'] = str_or_none(traverse_obj(content, ('content', 'contentTitle')))
            return video_data

        for content in json_data.get('content') or []:
            video_data = real_get_video_data(content)

            if not video_data:
                continue

            yield self.url_result(url=video_data.get('url'), video_id=video_data.get('id'), video_title=str_or_none(video_data.get('title')))


# Stack is an aggregation of content. On the website, stacks are shown as a collection of videos
# or other materials stacked over each other.
class RokfinStackIE(RokfinPlaylistIE):
    IE_NAME = 'rokfin:stack'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/stack/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.rokfin.com/stack/271/Tulsi-Gabbard-Portsmouth-Townhall-FULL--Feb-9-2020',
        'info_dict': {
            'id': 271,
            'ext': 'mp4'
        }
    }]

    def _real_extract(self, url_from_user):
        _META_VIDEO_DATA_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/stack/'
        _VIDEO_BASE_URL = 'https://rokfin.com/'
        _RECOMMENDED_STACK_BASE_URL = 'https://rokfin.com/stack/'
        list_id = self._match_id(url_from_user)

        return self.playlist_result(
            entries=self._get_video_data(
                json_data=self._download_json(_META_VIDEO_DATA_BASE_URL + list_id, list_id, fatal=False) or {},
                video_base_url=_VIDEO_BASE_URL),
            playlist_id=list_id,
            webpage_url=_RECOMMENDED_STACK_BASE_URL + list_id,
            # webpage_url = url_from_user minus the final part. The final part exists solely for human consumption and is otherwise irrelevant.
            original_url=url_from_user)


class RokfinChannelIE(RokfinPlaylistIE):
    IE_NAME = 'rokfin:channel'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?!((feed/?)|(discover/?)|(channels/?))$)(?P<id>[^/]+)/?$'
    _TESTS = [{
        'url': 'https://rokfin.com/TheConvoCouch',
        'info_dict': {
            'id': 12071,
            'description': 'Independent media providing news and commentary in our studio but also on the ground. We stand by our principles regardless of party lines & are willing to sit down and have convos with most anybody.',
            'ext': 'mp4'
        }
    }]

    def _real_extract(self, url_from_user):
        _CHANNEL_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/user/'
        _RECOMMENDED_CHANNEL_BASE_URL = 'https://rokfin.com/'

        def dnl_video_meta_data_incrementally(channel_id, tab, channel_username, channel_base_url):
            _VIDEO_BASE_URL = 'https://rokfin.com/'
            _META_DATA_BASE_URL2 = 'https://prod-api-v2.production.rokfin.com/api/v2/public/post/search/'
            _ENTRIES_PER_REQUEST = 50  # 50 is the maximum Rokfin permits per request.
            pages_total = None

            for page_n in itertools.count(0):
                if tab in ('posts', 'top'):
                    data_url = f'{channel_base_url}{channel_username}/{tab}?page={page_n}&size={_ENTRIES_PER_REQUEST}'
                else:
                    data_url = f'{_META_DATA_BASE_URL2}{tab}?page={page_n}&size={_ENTRIES_PER_REQUEST}&creator={channel_id}'

                downloaded_json_meta_data = self._download_json(data_url, channel_username, note=f'Downloading video metadata (page {page_n + 1}' + (f' of {pages_total}' if pages_total else '') + ')', fatal=False) or {}

                yield from self._get_video_data(json_data=downloaded_json_meta_data, video_base_url=_VIDEO_BASE_URL)

                pages_total = downloaded_json_meta_data.get('totalPages')
                is_last_page = try_get(downloaded_json_meta_data, lambda x: x['last'] is True)
                max_page_count_reached = try_get(pages_total, lambda x: page_n + 1 >= x)

                if is_last_page or max_page_count_reached or ((is_last_page is None) and (max_page_count_reached is None)):
                    return []
                # The final and-condition is a mere safety check.

        tabs = self._configuration_arg('content')
        tab_dic = {'new': 'posts', 'top': 'top', 'videos': 'video', 'podcasts': 'audio', 'streams': 'stream', 'articles': 'article', 'rankings': 'ranking', 'stacks': 'stack'}

        if len(tabs) > 1 or (len(tabs) == 1 and tabs[0] not in tab_dic.keys()):
            raise ExtractorError(msg='usage: --extractor-args "rokfinchannel:content=[new|top|videos|podcasts|streams|articles|rankings|stacks]"', expected=True)

        channel_username = self._match_id(url_from_user)
        channel_info = self._download_json(_CHANNEL_BASE_URL + channel_username, channel_username, fatal=False) or {}
        channel_id = channel_info.get('id')

        if channel_id:
            return self.playlist_result(
                entries=dnl_video_meta_data_incrementally(tab=tab_dic[tabs[0] if tabs else "new"], channel_id=channel_id, channel_username=channel_username, channel_base_url=_CHANNEL_BASE_URL),
                playlist_id=channel_id,
                playlist_title=channel_username,
                playlist_description=str_or_none(channel_info.get('description')),
                webpage_url=_RECOMMENDED_CHANNEL_BASE_URL + channel_username,
                # webpage_url = url_from_user minus the final part. The final part exists solely for human consumption and is otherwise irrelevant.
                original_url=url_from_user)
        else:
            raise ExtractorError(msg='unknown channel', expected=True)


# E.g.: rkfnsearch5:"zelenko" or rkfnsearch5:"\"dr mollie james\""
class RokfinSearchIE(SearchInfoExtractor):
    IE_NAME = 'rokfin:search'
    _SEARCH_KEY = 'rkfnsearch'

    service_url = None
    service_access_key = None

    def _get_n_results(self, query, n_results):
        def dnl_video_meta_data_incrementally(query, n_results):
            if n_results <= 0:
                return

            ENTRIES_PER_PAGE = 100
            max_pages_to_download = None if n_results == float('inf') else ceil(n_results / ENTRIES_PER_PAGE)
            pages_total = None  # The # of pages containing search results, as reported by Rokfin.
            pages_total_printed = False  # Makes sure pages_total is not printed more than once.
            results_total_printed = False  # Makes sure the total number of search results is not printed more than once.
            yielded_result_counter = 0  # How many search results have been yielded?
            POST_DATA = {'query': query, 'page': {'size': ENTRIES_PER_PAGE}, 'facets': {'content_type': {'type': 'value', 'size': ENTRIES_PER_PAGE}, 'creator_name': {'type': 'value', 'size': ENTRIES_PER_PAGE}, 'premium_plan': {'type': 'value', 'size': ENTRIES_PER_PAGE}}, 'result_fields': {'creator_twitter': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_id': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_username': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_instagram': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'post_comments': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'post_text': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_description': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_title': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'post_updated_at': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_youtube': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_type': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_name': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_facebook': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'id': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'premium_plan': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}}}

            for page_n in itertools.count(1) if n_results == float('inf') else range(1, max_pages_to_download + 1):
                POST_DATA['page']['current'] = page_n

                if self.service_url and self.service_access_key:
                    # Access has already been established.
                    srch_res = self._download_json(
                        self.service_url,
                        self._SEARCH_KEY,
                        headers={'authorization': self.service_access_key},
                        data=dumps(POST_DATA).encode('utf-8'),
                        encoding='utf-8',
                        note=f'Downloading search results (page {page_n}' + (f' of {min(pages_total, max_pages_to_download)}' if pages_total is not None and max_pages_to_download is not None else '') + ')',
                        fatal=True)
                else:
                    self.write_debug(msg='gaining access')
                    (service_urls, service_access_keys) = self._get_access_credentials()

                    # Try all possible combinations between service_urls and service_access_keys and see which one works.
                    # This should succeed on the first attempt, but no one knows for sure.
                    for service_url, service_access_key in itertools.product(service_urls, service_access_keys):
                        self.write_debug(msg=f'attempting to download 1st batch of search results from "{service_url}" using access key "{service_access_key}"')
                        srch_res = self._download_json(
                            service_url,
                            self._SEARCH_KEY,
                            headers={'authorization': service_access_key},
                            data=dumps(POST_DATA).encode('utf-8'),
                            encoding='utf-8',
                            note='Downloading search results (page 1)',
                            fatal=False) or {}

                        if srch_res:
                            self.service_url = service_url
                            self.service_access_key = service_access_key
                            self.write_debug(msg='download succeeded, access gained')
                            break
                        else:
                            self.write_debug(msg='download failed: access denied. Still trying...')
                    else:
                        raise ExtractorError(msg='couldn\'t gain access', expected=False)

                def get_video_data(content):
                    BASE_URL = 'https://rokfin.com/'
                    content_type = try_get(content, lambda x: x['content_type']['raw'])
                    fn = try_get(content_type, lambda y: {
                        'video': lambda x: {'id': int(x['id']['raw']), 'url': f'{BASE_URL}post/{int(x["id"]["raw"])}'},
                        'audio': lambda x: {'id': int(x['id']['raw']), 'url': f'{BASE_URL}post/{int(x["id"]["raw"])}'},
                        'stream': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}stream/{int(x["content_id"]["raw"])}'},
                        'dead_stream': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}stream/{int(x["content_id"]["raw"])}'},
                        'stack': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}stack/{int(x["content_id"]["raw"])}'},
                        'article': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}article/{int(x["content_id"]["raw"])}'},
                        'ranking': lambda x: {'id': int(x['content_id']['raw']), 'url': f'{BASE_URL}ranking/{int(x["content_id"]["raw"])}'}
                    }[y])

                    if fn is None:
                        self.to_screen('non-downloadable content ignored' + ('' if self.get_param('verbose') else '. Use --verbose for details'))
                        self.write_debug(f'unprocessed entry: {content}')
                        return

                    video_data = try_get(content, fn)
                    if video_data is None:
                        self.write_debug(f'{content_type}: could not process content entry: {content}')
                        return

                    video_data['url'] = url_or_none(video_data.get('url'))

                    if video_data.get('url') is None:
                        self.to_screen('entry with missing or malformed URL ignored' + ('' if self.get_param('verbose') else '. Use --verbose for details'))
                        self.write_debug(f'{content_type}: could not process content entry: {content}')
                        return

                    video_data['title'] = str_or_none(traverse_obj(content, ('content_title', 'raw')))
                    return video_data

                pages_total = int_or_none(traverse_obj(srch_res, ('meta', 'page', 'total_pages')))
                if pages_total is None:
                    self.report_warning(msg='unknown total # of pages of search results. This may be a bug', only_once=True)
                elif (pages_total_printed is False) and max_pages_to_download is not None:
                    self.to_screen(msg=f'Pages to download: {min(pages_total, max_pages_to_download)}')
                    pages_total_printed = True

                results_total = int_or_none(traverse_obj(srch_res, ('meta', 'page', 'total_results')))
                if results_total is None:
                    self.report_warning(msg='unknown total # of search results. This may be a bug', only_once=True)
                elif results_total_printed is False:
                    self.to_screen(msg=f'Search results available: {results_total}')
                    results_total_printed = True

                for content in srch_res.get('results') or []:
                    video_data = get_video_data(content)

                    if not video_data:
                        continue

                    yield self.url_result(url=video_data.get('url'), video_id=video_data.get('id'), video_title=video_data.get('title'))
                    yielded_result_counter += 1

                    if yielded_result_counter >= min(n_results, results_total or float('inf')) or (n_results == float('inf') and results_total is None):
                        '''
                        If Rokfin (unexpectedly) does not report the total # of search results,
                        and n_results == inf, then the downloading loop has no definitive stopping point
                        and could, theoritically, execute indefinitely. To prevent this, we proactively
                        quit the loop.

                        The good news is: this is an unlikely scenario and should not occur routinely.
                        '''
                        if n_results == float('inf') and results_total is None:
                            self.report_warning(msg='please specify a finite number of search results, e.g. 100, and re-run. Stopping the downloading process prematurely to avoid an infinite loop')

                        return

                if page_n >= min(pages_total or float('inf'), max_pages_to_download or float('inf')) or (pages_total is None and max_pages_to_download is None):
                    return

        return self.playlist_result(
            entries=dnl_video_meta_data_incrementally(query, n_results),
            playlist_id=query)

    def _get_access_credentials(self):
        if self.service_url and self.service_access_key:
            return

        STARTING_WP_URL = 'https://rokfin.com/discover'
        SERVICE_URL_PATH = '/api/as/v1/engines/rokfin-search/search.json'
        BASE_URL = 'https://rokfin.com'

        notfound_err_page = self._download_webpage(
            STARTING_WP_URL,
            self._SEARCH_KEY,
            expected_status=404,  # 'Not Found' is the expected outcome here.
            fatal=False)

        js = ''
        # <script src="/static/js/<filename>">
        for m in try_get(notfound_err_page, lambda x: finditer(r'<script\s+[^>]*?src\s*=\s*"(?P<path>/static/js/[^">]*)"[^>]*>', x)) or []:
            try:
                js = js + try_get(m, lambda x: self._download_webpage(
                    BASE_URL + x.group('path'),
                    self._SEARCH_KEY,
                    note='Downloading JavaScript file',
                    fatal=False))
            except TypeError:  # TypeError happens when try_get returns a non-string.
                pass

        service_urls = []
        services_access_keys = []
        for m in finditer(r'(REACT_APP_SEARCH_KEY\s*:\s*"(?P<key>[^"]*)")|(REACT_APP_ENDPOINT_BASE\s*:\s*"(?P<url>[^"]*)")', js):
            if m.group('url'):
                service_urls.append(m.group('url') + SERVICE_URL_PATH)
            elif m.group('key'):
                services_access_keys.append('Bearer ' + m.group('key'))

        return (service_urls, services_access_keys)
