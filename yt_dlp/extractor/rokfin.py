# coding: utf-8
from json import (
    dumps as json_dumps,
)
from math import ceil as math_ceil
from itertools import (
    count as itertools_count,
    product as itertools_product,
)
import datetime
from re import finditer as re_finditer
from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    unified_timestamp,
    try_get,
    traverse_obj,
    int_or_none,
    bool_or_none,
    float_or_none,
    url_or_none,
    ExtractorError,
)


class RokfinSingleVideoIE(InfoExtractor):
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
            'is_live': False,
            'was_live': False,
            'live_status': 'not_live'
        }
    }]

    def _real_extract(self, url_from_user):
        video_id = self._match_id(url_from_user)
        downloaded_json = self._download_json(self._META_DATA_BASE_URL + video_id, video_id, note='Downloading video metadata', fatal=False) or {}

        def videoAvailability(y, dic):
            video_availability = dic['premiumPlan']
            # 0 - public
            # 1 - premium only

            if video_availability not in (0, 1):
                y.report_warning(f'unknown availability code: {video_availability}. The extractor should be fixed')
                return

            return y._availability(
                is_private=False,
                needs_premium=(video_availability == 1),
                needs_subscription=False,
                needs_auth=False,
                is_unlisted=False)

        video_formats_url = url_or_none(traverse_obj(downloaded_json, ('content', 'contentUrl')))
        availability = try_get(self, lambda x: videoAvailability(x, downloaded_json))

        if video_formats_url:
            # Prior to adopting M3U, Rokfin stored videos directly in mp4 files:
            if video_formats_url.endswith('.mp4'):
                return self.url_result(url=video_formats_url, video_id=video_id, original_url=url_from_user)

            if not(video_formats_url.endswith('.m3u8')):
                self.raise_no_formats(msg=f'unsupported video URL {video_formats_url}', expected=False)

            frmts = self._extract_m3u8_formats(m3u8_url=video_formats_url, video_id=video_id, fatal=False)
            self._sort_formats(frmts)
        else:
            frmts = None

            if availability == 'premium_only':
                # The video is premium only.
                self.raise_no_formats(msg='premium content', expected=True)
            else:
                # We don't know why there is no (valid) video URL present.
                self.raise_no_formats(msg='unable to download: missing meta data', expected=True)

        content_subdict = lambda key: traverse_obj(downloaded_json, ('content', key))
        created_by = lambda key: traverse_obj(downloaded_json, ('createdBy', key))
        channel_name = traverse_obj(downloaded_json, ('createdBy', 'name'))
        downloaded_json_get = downloaded_json.get

        return {
            'id': video_id,
            'url': video_formats_url,
            'title': content_subdict('contentTitle'),
            'webpage_url': self._RECOMMENDED_VIDEO_BASE_URL + video_id,
            # The final part of url_from_user exists solely for human consumption and is otherwise skipped.
            'live_status': 'not_live',
            'duration': float_or_none(content_subdict('duration')),
            'thumbnail': content_subdict('thumbnailUrl1'),
            'description': content_subdict('contentDescription'),
            'like_count': downloaded_json_get('likeCount'),
            'dislike_count': downloaded_json_get('dislikeCount'),
            # 'comment_count': downloaded_json_get('numComments'), # Uncomment when Rf corrects the 'numComments' value.
            'availability': availability,
            'creator': channel_name,
            'channel_id': created_by('id'),
            'channel': channel_name,
            'channel_url': try_get(created_by, lambda x: self._CHANNEL_BASE_URL + x('username')),
            'timestamp': unified_timestamp(downloaded_json_get('creationDateTime')),
            'tags': [str(tag) for tag in downloaded_json_get('tags') or []],
            'formats': frmts or [],
            '__post_extractor': self.extract_comments(video_id=video_id)
        }

    def _get_comments(self, video_id):
        _COMMENTS_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/comment'
        _COMMENTS_PER_REQUEST = 50  # 50 is the maximum Rokfin permits per request.

        def dnl_comments_incrementally(base_url, video_id, comments_per_page):
            pages_total = None
            _download_json = self._download_json

            for page_n in itertools_count(0):
                raw_comments = _download_json(
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
                comment = comment.get
                comment_text = comment('comment')

                if not isinstance(comment_text, str):
                    continue

                yield {
                    'text': comment_text,
                    'author': comment('name'),
                    'id': comment('commentId'),
                    'author_id': comment('userId'),
                    'parent': 'root',
                    'like_count': comment('numLikes'),
                    'dislike_count': comment('numDislikes'),
                    'timestamp': unified_timestamp(comment('postedAt'))
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
        video_id = self._match_id(url_from_user)
        downloaded_json = self._download_json(self._META_DATA_BASE_URL + video_id, video_id, note='Downloading video metadata', fatal=False) or {}
        m3u8_url = try_get(downloaded_json, lambda x: url_or_none(x['url']))
        availability = try_get(self, lambda x: x._availability(
            needs_premium=True if downloaded_json['premium'] else False,
            is_private=False,
            needs_subscription=False,
            needs_auth=False,
            is_unlisted=False))
        downloaded_json = downloaded_json.get

        stream_scheduled_for = try_get(downloaded_json, lambda x: datetime.datetime.strptime(x('scheduledAt'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc))
        # 'scheduledAt' is set to None after the stream becomes live.

        stream_ended_at = try_get(
            downloaded_json,
            lambda x: datetime.datetime.strptime(
                x('stoppedAt'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc))
        # 'stoppedAt' is null unless the stream is finished. 'stoppedAt' likely contains an incorrect value,
        # so what matters to us is whether or not this field is *present*.

        if m3u8_url:
            frmts = self._extract_m3u8_formats(m3u8_url=m3u8_url, video_id=video_id, fatal=False, live=(stream_ended_at is None))
            self._sort_formats(frmts)
        else:
            frmts = None

        if not frmts:
            if stream_scheduled_for:
                # The stream is pending.
                self.raise_no_formats(
                    msg='the ' + ('premium-only ' if availability == 'premium_only' else '')
                    + 'stream is/was expected to start at '
                    + datetime.datetime.strftime(stream_scheduled_for, '%Y-%m-%dT%H:%M:%S') + ' (YYYY-MM-DD, 24H clock, GMT)' + ('' if self.get_param('wait_for_video') else '. Consider adding --wait-for-video'),
                    video_id=video_id,
                    expected=True)
            elif availability == 'premium_only':
                self.raise_no_formats(msg='premium content', video_id=video_id, expected=True)
            elif m3u8_url:
                self.raise_no_formats(msg='unable to download: missing meta data', video_id=video_id, expected=True)
            else:
                # We don't know why there is no (valid) meta data present.
                self.raise_no_formats(msg='unable to download: don\'t know where to find meta data', video_id=video_id, expected=True)

            # Self-reminder: --wait-for-video causes raise_no_formats(... expected=True ...) to print a warning message
            # and quit without raising ExtractorError.

        # 'postedAtMilli' shows when the stream (live or pending) appeared on Rokfin. As soon as a pending stream goes live,
        # the value of 'postedAtMilli' will change to reflect the stream's starting time.
        stream_started_at_timestamp = try_get(downloaded_json, lambda x: x('postedAtMilli') / 1000) if stream_scheduled_for is None else None
        stream_started_at = try_get(stream_started_at_timestamp, lambda x: datetime.datetime.utcfromtimestamp(x).replace(tzinfo=datetime.timezone.utc))
        created_by = lambda x: try_get(downloaded_json, lambda y: y('creator').get(x))
        channel_name = created_by('name')
        channel_id = created_by('id')
        release_timestamp = try_get(stream_scheduled_for, lambda x: unified_timestamp(datetime.datetime.strftime(x, '%Y-%m-%dT%H:%M:%S'))) or stream_started_at_timestamp

        return {
            'id': video_id,
            'url': m3u8_url,
            'original_url': url_from_user,
            'title': downloaded_json('title'),
            'webpage_url': self._RECOMMENDED_VIDEO_BASE_URL + video_id,
            # The final part of url_from_user exists solely for human consumption and is otherwise skipped.
            'manifest_url': m3u8_url,
            'thumbnail': downloaded_json('thumbnail'),
            'description': downloaded_json('description'),
            'like_count': downloaded_json('likeCount'),
            'dislike_count': downloaded_json('dislikeCount'),
            'creator': channel_name,
            'channel': channel_name,
            'channel_id': channel_id,
            'uploader_id': channel_id,
            'channel_url': try_get(created_by, lambda x: self._CHANNEL_BASE_URL + x('username')),
            'availability': availability,
            'tags': [str(tag) for tag in downloaded_json('tags') or []],
            'live_status': 'was_live' if stream_ended_at else
                           'is_live' if stream_scheduled_for is None else
                           'is_upcoming',
            # Remove the 'False and' part when Rokfin corrects the 'stoppedAt' value:
            'duration': (stream_ended_at - stream_started_at).total_seconds() if False and stream_started_at and stream_ended_at else None,
            'timestamp': release_timestamp,
            'release_timestamp': release_timestamp,
            'formats': frmts or []
        }


class RokfinPlaylistIE(InfoExtractor):
    def _get_video_data(self, json_data, video_base_url):
        write_debug = self.write_debug
        to_screen = self.to_screen
        url_result = self.url_result

        def get_video_url(content):
            media_type = try_get(content, lambda x: x['mediaType'])
            fn = try_get(media_type, lambda y: {
                'video': lambda x: f'{video_base_url}post/{x["id"]}',
                'audio': lambda x: f'{video_base_url}post/{x["id"]}',
                'stream': lambda x: f'{video_base_url}stream/{x["mediaId"]}',
                'dead_stream': lambda x: f'{video_base_url}stream/{x["mediaId"]}',
                'stack': lambda x: f'{video_base_url}stack/{x["mediaId"]}',
                'article': lambda x: f'{video_base_url}article/{x["mediaId"]}',
                'ranking': lambda x: f'{video_base_url}ranking/{x["mediaId"]}'
            }[y])

            if fn is None:
                to_screen('skipping unsupported media type' + ('' if media_type is None else f': {media_type}') + ('' if self.get_param('verbose') else '. Use --verbose to learn more'))
                write_debug(f'could not process content entry: {content}')
                return

            video_url = try_get(content, fn)
            if video_url is None:
                write_debug(f'{media_type}: could not process content entry: {content}')

            return video_url

        for content in try_get(json_data, lambda x: x['content']) or []:
            video_url = get_video_url(content)

            if video_url:
                yield url_result(url=video_url)


# A stack is an aggregation of content. On the website, stacks are shown as a collection of videos
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
                json_data=self._download_json(_META_VIDEO_DATA_BASE_URL + list_id, list_id, note='Downloading playlist info', fatal=False) or {},
                video_base_url=_VIDEO_BASE_URL),
            playlist_id=list_id,
            webpage_url=_RECOMMENDED_STACK_BASE_URL + list_id,
            # The final part of url_from_user exists solely for human consumption and is otherwise skipped.
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
            _download_json = self._download_json
            _get_video_data = self._get_video_data

            pages_total = None

            for page_n in itertools_count(0):
                if tab in ('posts', 'top'):
                    data_url = f'{channel_base_url}{channel_username}/{tab}?page={page_n}&size={_ENTRIES_PER_REQUEST}'
                else:
                    data_url = f'{_META_DATA_BASE_URL2}{tab}?page={page_n}&size={_ENTRIES_PER_REQUEST}&creator={channel_id}'

                downloaded_json = _download_json(data_url, channel_username, note=f'Downloading video metadata (page {page_n + 1}' + (f' of {pages_total}' if pages_total else '') + ')', fatal=False) or {}

                yield from _get_video_data(json_data=downloaded_json, video_base_url=_VIDEO_BASE_URL)

                pages_total = try_get(downloaded_json, lambda x: x['totalPages'])
                is_last_page = try_get(downloaded_json, lambda x: x['last'] is True)
                max_page_count_reached = try_get(pages_total, lambda x: page_n + 1 >= x)

                if is_last_page or max_page_count_reached or ((is_last_page is None) and (max_page_count_reached is None)):
                    return []
                # The final and-condition is a mere safety check.

        tabs = self._configuration_arg('content')
        tab_dic = {'new': 'posts', 'top': 'top', 'videos': 'video', 'podcasts': 'audio', 'streams': 'stream', 'articles': 'article', 'rankings': 'ranking', 'stacks': 'stack'}

        if len(tabs) > 1 or (len(tabs) == 1 and tabs[0] not in tab_dic.keys()):
            raise ExtractorError(msg='usage: --extractor-args "rokfinchannel:content=[new|top|videos|podcasts|streams|articles|rankings|stacks]"', expected=True)

        channel_username = self._match_id(url_from_user)
        channel_info = self._download_json(_CHANNEL_BASE_URL + channel_username, channel_username, note='Downloading channel info', fatal=False) or {}
        channel_id = try_get(channel_info, lambda x: x['id'])

        return self.playlist_result(
            entries=dnl_video_meta_data_incrementally(tab=tab_dic[tabs[0] if tabs else "new"], channel_id=channel_id, channel_username=channel_username, channel_base_url=_CHANNEL_BASE_URL),
            playlist_id=channel_id,
            playlist_description=try_get(channel_info, lambda x: x['description']),
            webpage_url=_RECOMMENDED_CHANNEL_BASE_URL + channel_username,
            # The final part of url_from_user exists solely for human consumption and is otherwise skipped.
            original_url=url_from_user)


# E.g.: rkfnsearch5:"dr mollie james" or rkfnsearch5:"\"dr mollie james\""
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
            max_pages_to_download = None if n_results == float('inf') else math_ceil(n_results / ENTRIES_PER_PAGE)
            url_result = self.url_result
            _download_json = self._download_json
            _SEARCH_KEY = self._SEARCH_KEY
            report_warning = self.report_warning
            write_debug = self.write_debug
            to_screen = self.to_screen
            pages_total = None  # The # of pages containing search results, as reported by Rokfin.
            pages_total_printed = False  # Makes sure pages_total is not printed more than once.
            results_total_printed = False  # Makes sure the total number of search results is not printed more than once.
            result_counter = 0  # How many search results have been yielded?
            POST_DATA = {'query': query, 'page': {'size': ENTRIES_PER_PAGE}, 'facets': {'content_type': {'type': 'value', 'size': ENTRIES_PER_PAGE}, 'creator_name': {'type': 'value', 'size': ENTRIES_PER_PAGE}, 'premium_plan': {'type': 'value', 'size': ENTRIES_PER_PAGE}}, 'result_fields': {'creator_twitter': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_id': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_username': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_instagram': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'post_comments': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'post_text': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_description': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_title': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'post_updated_at': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_youtube': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'content_type': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_name': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'creator_facebook': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'id': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}, 'premium_plan': {'raw': {}, 'snippet': {'size': ENTRIES_PER_PAGE, 'fallback': True}}}}

            for page_n in itertools_count(1) if n_results == float('inf') else range(1, max_pages_to_download + 1):
                POST_DATA['page']['current'] = page_n

                if self.service_url and self.service_access_key:
                    # Access has already been established.
                    srch_res = _download_json(
                        self.service_url,
                        _SEARCH_KEY,
                        headers={'authorization': self.service_access_key},
                        data=json_dumps(POST_DATA).encode('utf8'),
                        encoding='utf8',
                        note=f'Downloading search results (page {page_n}' + (f' of {min(pages_total, max_pages_to_download)}' if pages_total is not None and max_pages_to_download is not None else '') + ')',
                        fatal=True)
                else:
                    write_debug(msg='gaining access')
                    (service_urls, service_access_keys) = self._get_access_credentials()

                    # Try all possible combinations between service_urls and service_access_keys and see which one works.
                    # This should succeed on the first attempt, but no one knows for sure.
                    for service_url, service_access_key in itertools_product(service_urls, service_access_keys):
                        write_debug(msg=f'attempting to download 1st batch of search results from "{service_url}" using access key "{service_access_key}"')
                        srch_res = _download_json(
                            service_url,
                            _SEARCH_KEY,
                            headers={'authorization': service_access_key},
                            data=json_dumps(POST_DATA).encode('utf8'),
                            encoding='utf8',
                            note='Downloading search results (page 1)',
                            fatal=False)

                        if srch_res is not None:
                            self.service_url = service_url
                            self.service_access_key = service_access_key
                            write_debug(msg='download succeeded, access gained')
                            break
                        else:
                            write_debug(msg='download failed: access denied. Still trying...')
                    else:
                        raise ExtractorError(msg='couldn\'t gain access', expected=False)

                def get_video_url(content):
                    BASE_URL = 'https://rokfin.com/'
                    content_type = try_get(content, lambda x: x['content_type']['raw'])
                    fn = try_get(content_type, lambda y: {
                        'video': lambda x: f'{BASE_URL}post/{int(x["id"]["raw"])}',
                        'audio': lambda x: f'{BASE_URL}post/{int(x["id"]["raw"])}',
                        'stream': lambda x: f'{BASE_URL}stream/{int(x["content_id"]["raw"])}',
                        'dead_stream': lambda x: f'{BASE_URL}stream/{int(x["content_id"]["raw"])}',
                        'stack': lambda x: f'{BASE_URL}stack/{int(x["content_id"]["raw"])}',
                        'article': lambda x: f'{BASE_URL}article/{int(x["content_id"]["raw"])}',
                        'ranking': lambda x: f'{BASE_URL}ranking/{int(x["content_id"]["raw"])}'
                    }[y])

                    if fn is None:
                        to_screen('skipping unsupported content type' + ('' if content_type is None else f': {content_type}') + ('' if not self.get_param('verbose') else '. Use --verbose to learn more'))
                        write_debug(f'could not process content entry: {content}')
                        return

                    video_url = try_get(content, fn)
                    if video_url is None:
                        write_debug(f'{content_type}: could not process content entry: {content}')

                    return video_url

                pages_total = int_or_none(traverse_obj(srch_res, ('meta', 'page', 'total_pages')))
                if pages_total is None:
                    report_warning(msg='unknown total # of pages of search results. This may be a bug', only_once=True)
                elif (pages_total_printed is False) and max_pages_to_download is not None:
                    to_screen(msg=f'Pages to download: {min(pages_total, max_pages_to_download)}')
                    pages_total_printed = True

                results_total = int_or_none(traverse_obj(srch_res, ('meta', 'page', 'total_results')))
                if results_total is None:
                    report_warning(msg='unknown total # of search results. This may be a bug', only_once=True)
                elif results_total_printed is False:
                    to_screen(msg=f'Search results available: {results_total}')
                    results_total_printed = True

                for content in srch_res.get('results') or []:
                    video_url = get_video_url(content)

                    if video_url:
                        yield url_result(video_url)

                        result_counter += 1

                        if result_counter >= min(n_results, results_total or float('inf')) or (n_results == float('inf') and results_total is None):
                            # If n_results == inf, and Rokfin does not report the total # of search
                            # results available, then we have no definitive stopping point, so
                            # the downloading process could execute indefinitely. To address this,
                            # we play it safe and quit.
                            if n_results == float('inf') and results_total is None:
                                report_warning(msg='please specify a finite number of search results, e.g. 100, and re-run. Stopping the downloading process prematurely to avoid an infinite loop')

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

        # The following returns 404 (Not Found) which is intended:
        starting_wp_content = self._download_webpage(
            url_or_request=STARTING_WP_URL,
            video_id=self._SEARCH_KEY,
            note='Downloading webpage',
            expected_status=404,
            fatal=False)

        js = ''
        # <script src="/static/js/<filename>">
        for m in try_get(starting_wp_content, lambda x: re_finditer(r'<script\s+[^>]*?src\s*=\s*"(?P<path>/static/js/[^">]*)"[^>]*>', x)) or []:
            try:
                js = js + try_get(m, lambda x: self._download_webpage(
                    url_or_request=BASE_URL + x.group('path'),
                    video_id=self._SEARCH_KEY,
                    note='Downloading JavaScript file',
                    fatal=False))
            except TypeError:  # TypeError happens when try_get returns None.
                pass

        service_urls = []
        services_access_keys = []
        for m in re_finditer(r'(REACT_APP_SEARCH_KEY\s*:\s*"(?P<key>[^"]*)")|(REACT_APP_ENDPOINT_BASE\s*:\s*"(?P<url>[^"]*)")', js):
            if m.group('url'):
                service_urls.append(m.group('url') + SERVICE_URL_PATH)
            elif m.group('key'):
                services_access_keys.append('Bearer ' + m.group('key'))

        return (service_urls, services_access_keys)
