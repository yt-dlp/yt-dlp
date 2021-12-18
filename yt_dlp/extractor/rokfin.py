# coding: utf-8
from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    unified_timestamp,
    try_get,
    float_or_none,
    url_or_none,
    preferredencoding,
    ExtractorError
)


# Rokfin treats each video as either a stream or a "post". Streams include active
# and pending live streams and their recordings. Pre-made videos are called "posts".


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
            'thumbnail': 'https://img.production.rokfin.com/eyJidWNrZXQiOiJya2ZuLXByb2R1Y3Rpb24tbWVkaWEiLCJrZXkiOiIvdXNlci82NTQyOS9wb3N0L2RhMjBkOTYwLTI0OTMtNDA0My04ZDEwLTIwMjBlZDc3NjY0MC90aHVtYm5haWwvMGU3YzMyOTYtM2YwZi00ZmQ1LWIyODYtN2I5OGRmNjcyYmQyIiwiZWRpdHMiOnsicmVzaXplIjp7IndpZHRoIjo2MDAsImhlaWdodCI6MzM3LCJmaXQiOiJjb3ZlciJ9fX0=',
            'upload_date': '20211023',
            'timestamp': 1634998029,
            'creator': 'Jimmy Dore',
            'channel': 'Jimmy Dore',
            'channel_id': 65429,
            'channel_url': 'https://rokfin.com/TheJimmyDoreShow',
            'description': None,
            'duration': 213.0,
            'availability': 'public',
            'is_live': False,
            'was_live': False,
            'live_status': 'not_live'
        }
    }]

    def _real_extract(self, url_from_user):
        video_id = self._match_id(url_from_user)
        downloaded_json = self._download_json(url_or_request=self._META_DATA_BASE_URL + video_id, video_id=video_id, note='Downloading video metadata', fatal=False)

        def videoAvailability(y, dic):
            video_availability = dic['premiumPlan']
            # 0 - public
            # 1 - premium only

            if video_availability not in (0, 1):
                y.report_warning(
                    'unknown availability code: ' + str(video_availability) + '. The extractor should be fixed')
                return None

            return y._availability(
                is_private=False,
                needs_premium=(video_availability == 1),
                needs_subscription=False,
                needs_auth=False,
                is_unlisted=False)

        content_subdict = try_get(downloaded_json, lambda x: x['content'])
        video_formats_url = try_get(content_subdict, lambda x: url_or_none(x['contentUrl']))
        availability = try_get(self, lambda x: videoAvailability(x, downloaded_json))

        if video_formats_url:
            # Prior to adopting M3U, Rokfin stored videos directly in regular mp4 files:
            if video_formats_url.endswith('.mp4'):
                return self.url_result(url=video_formats_url)

            if not(video_formats_url.endswith('.m3u8')):
                self.raise_no_formats(msg=f'unsupported video URL {video_formats_url}', expected=False)

            frmts = self._extract_m3u8_formats(m3u8_url=video_formats_url, video_id=video_id, fatal=False)
            self._sort_formats(frmts)
        else:
            frmts = None

            if availability == 'premium_only':
                # The video is premium only.
                self.raise_no_formats(msg='unable to download premium content', expected=True)
            else:
                # We don't know why there is no (valid) video URL present.
                self.raise_no_formats(msg='unable to proceed due to missing meta data', expected=True)

        downloaded_json = try_get(downloaded_json, lambda x: x.get)
        created_by = try_get(downloaded_json, lambda x: x('createdBy')).get
        upload_date_time = try_get(downloaded_json, lambda x: x('creationDateTime'))
        channel_name = try_get(created_by, lambda x: x('name'))
        content_subdict = try_get(content_subdict, lambda x: x.get)

        return {
            'id': video_id,
            'url': video_formats_url,
            'title': try_get(content_subdict, lambda x: x('contentTitle')),
            'webpage_url': self._RECOMMENDED_VIDEO_BASE_URL + video_id,
            'manifest_url': video_formats_url,
            'is_live': False,
            'was_live': False,
            'duration': try_get(content_subdict, lambda x: float_or_none(x('duration'))),
            'thumbnail': try_get(content_subdict, lambda x: x('thumbnailUrl1')),
            'description': try_get(content_subdict, lambda x: x('contentDescription')),
            'like_count': try_get(downloaded_json, lambda x: x('likeCount')),
            'dislike_count': try_get(downloaded_json, lambda x: x('dislikeCount')),
            'comment_count': try_get(downloaded_json, lambda x: x('numComments')),
            'availability': availability,
            'creator': channel_name,
            'channel_id': try_get(created_by, lambda x: x('id')),
            'channel': channel_name,
            'channel_url': try_get(created_by, lambda x: self._CHANNEL_BASE_URL + x('username')),
            'timestamp': unified_timestamp(upload_date_time),
            'tags': [str(tag) for tag in try_get(downloaded_json, lambda x: x('tags')) or []],
            'formats': frmts or [],
            '__post_extractor': self.extract_comments(video_id=video_id)
        }

    def _get_comments(self, video_id):
        import itertools

        _COMMENTS_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/comment'
        _COMMENTS_PER_REQUEST = 50  # 50 is the maximum Rokfin permits per request.

        def dnl_comments_incrementally(base_url, video_id, comments_per_page):
            pages_total = None

            for page_n in itertools.count(0):
                raw_comments = self._download_json(
                    url_or_request=f'{base_url}?postId={video_id[5:]}&page={page_n}&size={comments_per_page}',
                    video_id=video_id,
                    note=f'Downloading viewer comments (page {page_n + 1}' + (f' of {pages_total}' if pages_total else '') + ')',
                    fatal=False)

                comments = try_get(raw_comments, lambda x: x['content'])
                pages_total = try_get(raw_comments, lambda x: x['totalPages'])
                is_last_page = try_get(raw_comments, lambda x: x['last'] is True)
                max_page_count_reached = try_get(raw_comments, lambda x: page_n + 1 >= pages_total)

                if comments:
                    yield comments

                if is_last_page or max_page_count_reached or ((is_last_page is None) and (max_page_count_reached is None)) or not(comments):
                    return
                # The last two conditions are safety checks.

        for page_of_comments in dnl_comments_incrementally(_COMMENTS_BASE_URL, video_id, _COMMENTS_PER_REQUEST):
            for comment in page_of_comments:
                comment_text = try_get(comment, lambda x: x['comment'])

                if isinstance(comment_text, str):
                    yield {
                        'text': comment_text,
                        'author': try_get(comment, lambda x: x['name']),
                        'id': try_get(comment, lambda x: x['commentId']),
                        'author_id': try_get(comment, lambda x: x['userId']),
                        'parent': 'root',
                        'like_count': try_get(comment, lambda x: x['numLikes']),
                        'dislike_count': try_get(comment, lambda x: x['numDislikes']),
                        'timestamp': try_get(comment, lambda x: unified_timestamp(x['postedAt']))
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
            'release_timestamp': 1635874720,
            'release_date': '20211102'
        }
    }]

    def _real_extract(self, url_from_user):
        import datetime

        video_id = self._match_id(url_from_user)
        downloaded_json = self._download_json(url_or_request=self._META_DATA_BASE_URL + video_id, video_id=video_id, note='Downloading video metadata', fatal=False)
        m3u8_url = try_get(downloaded_json, lambda x: url_or_none(x['url']))
        availability = try_get(self, lambda x: x._availability(
            needs_premium=True if downloaded_json['premium'] else False,
            is_private=False,
            needs_subscription=False,
            needs_auth=False,
            is_unlisted=False))
        downloaded_json = try_get(downloaded_json, lambda x: x.get)

        # Determine if the stream is pending:
        stream_scheduled_for = try_get(downloaded_json, lambda x: datetime.datetime.strptime(x('scheduledAt'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc))
        # None: the stream is not pending.
        # A valid datetime object: the stream will start at the given time.

        stream_ended_at = try_get(
            downloaded_json,
            lambda x: datetime.datetime.strptime(
                x('stoppedAt'), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc))
        # None: the stream is either live or pending.
        # A valid datetime object: the stream has ended at the given time.
        # This value is potentially incorrect. See the note below.

        if m3u8_url:
            frmts = self._extract_m3u8_formats(m3u8_url=m3u8_url, video_id=video_id, fatal=False, live=(stream_ended_at is None))
            self._sort_formats(frmts)
        else:
            frmts = None

            if stream_scheduled_for:
                # The stream is pending.
                self.raise_no_formats(
                    msg='the ' + ('premium-only ' if availability == 'premium_only' else '')
                    + 'stream starts at '
                    + datetime.datetime.strftime(stream_scheduled_for, '%Y-%m-%dT%H:%M:%S' + ' (YYYY-MM-DD, 24H clock, GMT). Consider adding --wait-for-video'),
                    expected=True)

            if availability == 'premium_only':
                # The stream is premium only.
                self.raise_no_formats(msg='unable to download premium content', expected=True)

            if not(stream_scheduled_for) and availability != 'premium_only':
                # We don't know why there is no (valid) video URL present.
                self.raise_no_formats(msg='unable to proceed due to missing meta data', expected=True)

        include_duration = False
        # If True, 'duration' will be added to the dictionary.
        #
        # As of November 2021, the 'stoppedAt' field in the meta data may be incorrect. This field contains
        # the end time of the stream. The error will cause the duration calculated from this meta data to be off,
        # as well. In one case, I've seen the duration being off by 5 minutes, for example. The only way to
        # get the correct value for the end time is by using the manifest. Doing this, however, would slow the
        # program down. As a compromise, I decided that omitting the duration is preferable to initializing it
        # with a wrong value (which the user will probably view as a bug anyway).

        # The 'postedAtMilli' field shows when the stream was posted. If the stream went live immediately, then
        # this field contains the starting time. If, however, the stream is pending, then its starting time
        # will be different, so the field is ignored. 'postedAtMilli' will contain the actual starting time,
        # once the stream has started.
        stream_started_at_timestamp = try_get(downloaded_json, lambda x: x('postedAtMilli') / 1000) if frmts or stream_ended_at else None
        stream_started_at = try_get(stream_started_at_timestamp, lambda x: datetime.datetime.utcfromtimestamp(x).replace(tzinfo=datetime.timezone.utc))

        if frmts or stream_ended_at:
            stream_scheduled_for = None

        def duration(started_at, ended_at):
            if started_at and ended_at:
                return (ended_at - started_at).total_seconds()

            return None

        created_by = try_get(downloaded_json, lambda x: x('creator').get)
        channel_name = try_get(created_by, lambda x: x('name'))

        return {
            'id': video_id,
            'url': m3u8_url,
            'title': try_get(downloaded_json, lambda x: x('title')),
            'webpage_url': self._RECOMMENDED_VIDEO_BASE_URL + video_id,
            'manifest_url': m3u8_url,
            'thumbnail': try_get(downloaded_json, lambda x: x('thumbnail')),
            'description': try_get(downloaded_json, lambda x: x('description')),
            'like_count': try_get(downloaded_json, lambda x: x('likeCount')),
            'dislike_count': try_get(downloaded_json, lambda x: x('dislikeCount')),
            'creator': channel_name,
            'channel_id': try_get(created_by, lambda x: x('id')),
            'uploader_id': try_get(created_by, lambda x: x('id')),
            'channel': channel_name,
            'channel_url': try_get(created_by, lambda x: self._CHANNEL_BASE_URL + x('username')),
            'availability': availability,
            'tags': [str(tag) for tag in try_get(downloaded_json, lambda x: x('tags')) or []],
            'is_live': (stream_ended_at is None) and bool(frmts),
            'was_live': m3u8_url is not None,
            'live_status': 'is_upcoming' if stream_scheduled_for and (m3u8_url is None) else None,
            'duration': duration(stream_started_at, stream_ended_at) if include_duration else None,
            'release_timestamp': try_get(stream_scheduled_for, lambda x: unified_timestamp(datetime.datetime.strftime(x, '%Y-%m-%dT%H:%M:%S'))) or stream_started_at_timestamp,
            'formats': frmts or []
        }


class RokfinPlaylistIE(InfoExtractor):
    def _get_video_data(self, json_data, video_base_url):
        write_debug = self.write_debug
        report_warning = self.report_warning
        url_result = self.url_result

        for content in try_get(json_data, lambda x: x['content']) or []:
            media_type = try_get(content, lambda x: x['mediaType'])

            if media_type in ('video', 'audio'):
                video_url = try_get(content, lambda x: f'{video_base_url}post/{x["id"]}')
                if video_url is None:
                    write_debug(msg=f'video: could not process content entry: {content}')
            elif media_type in ('stream', 'dead_stream'):
                video_url = try_get(content, lambda x: f'{video_base_url}stream/{x["mediaId"]}')
                if video_url is None:
                    write_debug(f'stream/dead_stream: could not process content entry: {content}')
            elif media_type == 'stack':
                video_url = try_get(content, lambda x: f'{video_base_url}stack/{x["mediaId"]}')
                if video_url is None:
                    write_debug(msg=f'stack: could not process content entry: {content}')
            elif media_type == 'article':
                video_url = try_get(content, lambda x: f'{video_base_url}article/{x["mediaId"]}')
                if video_url is None:
                    write_debug(msg=f'article: could not process content entry: {content}')
            elif media_type == 'ranking':
                video_url = try_get(content, lambda x: f'{video_base_url}ranking/{x["mediaId"]}')
                if video_url is None:
                    write_debug(msg=f'ranking: could not process content entry: {content}')
            else:
                video_url = None
                report_warning('skipping unsupported media type' + ('' if media_type is None else f': {media_type}') + '. Use --verbose to learn more')
                write_debug(f'could not process content entry: {content}')

            if video_url:
                yield url_result(url=video_url)


# A stack is just a playlist. On the website, stacks are shown as a collection of videos stacked
# over each other.
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
        list_video_data = self._download_json(url_or_request=_META_VIDEO_DATA_BASE_URL + list_id, video_id=list_id, note='Downloading playlist info', fatal=False)

        return self.playlist_result(
            entries=self._get_video_data(json_data=list_video_data, video_base_url=_VIDEO_BASE_URL),
            playlist_id=list_id,
            webpage_url=_RECOMMENDED_STACK_BASE_URL + list_id)


class RokfinChannelIE(RokfinPlaylistIE):
    IE_NAME = 'rokfin:channel'
    _VALID_URL = r'https?://(?:www\.)?rokfin\.com/(?P<id>[^/]+)/?$'
    _TESTS = [{
        'url': 'https://rokfin.com/TheConvoCouch',
        'info_dict': {
            'id': 12071,
            'description': 'Independent media providing news and commentary in our studio but also on the ground. We stand by our principles regardless of party lines & are willing to sit down and have convos with most anybody.',
            'ext': 'mp4'
        }
    }]

    def _real_extract(self, url_from_user):
        import itertools

        _ENTRIES_PER_REQUEST = 50  # 50 is the maximum Rokfin permits per request.
        _META_DATA_BASE_URL1 = 'https://prod-api-v2.production.rokfin.com/api/v2/public/user/'
        _RECOMMENDED_CHANNEL_BASE_URL = 'https://rokfin.com/'
        category_list = self._configuration_arg('category')
        category_dic = {'new': 'posts', 'top': 'top', 'videos': 'video', 'podcasts': 'audio', 'streams': 'stream', 'articles': 'article', 'rankings': 'ranking', 'stacks': 'stack'}

        if len(category_list) > 1 or (len(category_list) == 1 and category_list[0] not in category_dic.keys()):
            raise ExtractorError(msg='usage: --extractor-args "rokfinchannel:category=[new|top|videos|podcasts|streams|articles|rankings|stacks]"', expected=True)

        def dnl_video_meta_data_incrementally(pagesz, channel_id, category, channel_username):
            _VIDEO_BASE_URL = 'https://rokfin.com/'
            _META_DATA_BASE_URL2 = 'https://prod-api-v2.production.rokfin.com/api/v2/public/post/search/'

            pages_total = None

            for page_n in itertools.count(0):
                if category in ('posts', 'top'):
                    data_url = f'{_META_DATA_BASE_URL1}{channel_username}/{category}?page={page_n}&size={pagesz}'
                else:
                    data_url = f'{_META_DATA_BASE_URL2}{category}?page={page_n}&size={pagesz}&creator={channel_id}'

                downloaded_json = self._download_json(url_or_request=data_url, video_id=channel_username, note=f'Downloading video metadata (page {page_n + 1}' + (f' of {pages_total}' if pages_total else '') + ')', fatal=False)

                yield from self._get_video_data(json_data=downloaded_json, video_base_url=_VIDEO_BASE_URL)

                pages_total = try_get(downloaded_json, lambda x: x['totalPages'])
                is_last_page = try_get(downloaded_json, lambda x: x['last'] is True)
                max_page_count_reached = try_get(pages_total, lambda x: page_n + 1 >= x)

                if is_last_page or max_page_count_reached or ((is_last_page is None) and (max_page_count_reached is None)):
                    return []
                # The final and-condition is a mere safety check.

        channel_username = self._match_id(url_from_user)
        channel_info = self._download_json(url_or_request=_META_DATA_BASE_URL1 + channel_username, video_id=channel_username, note='Downloading channel info', fatal=False)
        channel_id = try_get(channel_info, lambda x: x['id'])

        return self.playlist_result(
            entries=dnl_video_meta_data_incrementally(pagesz=_ENTRIES_PER_REQUEST, category=category_dic[category_list[0] if category_list else "new"], channel_id=channel_id, channel_username=channel_username),
            playlist_id=channel_id,
            playlist_description=try_get(channel_info, lambda x: x['description']),
            webpage_url=_RECOMMENDED_CHANNEL_BASE_URL + channel_username)


class RokfinSearchIE(SearchInfoExtractor):
    IE_NAME = 'rokfin:search'
    _SEARCH_KEY = 'rkfnsearch'

    service_url = None
    service_access_key = None

    def _get_n_results(self, query, n_results):
        import json
        import math

        def dnl_video_meta_data_incrementally(query, n_results):
            import itertools

            if n_results <= 0:
                return

            BASE_URL = 'https://rokfin.com/'
            ENTRIES_PER_PAGE = 100

            (service_urls, service_access_keys) = self._get_access_credentials()

            enc = preferredencoding()
            pages_to_download = None if n_results == float('inf') else math.ceil(n_results / ENTRIES_PER_PAGE)
            url_result = self.url_result
            _download_webpage = self._download_webpage
            json_loads = json.loads
            _SEARCH_KEY = self._SEARCH_KEY
            report_warning = self.report_warning
            write_debug = self.write_debug
            ENTRIES_PER_PAGE_STR = str(ENTRIES_PER_PAGE)
            result_counter = 0

            for page_n in itertools.count(1) if n_results == float('inf') else range(1, pages_to_download + 1):
                POST_DATA = '{"query":"' + query + '","facets":{"content_type":{"type":"value","size":' + ENTRIES_PER_PAGE_STR + '},"creator_name":{"type":"value","size":' + ENTRIES_PER_PAGE_STR + '},"premium_plan":{"type":"value","size":' + ENTRIES_PER_PAGE_STR + '}},"result_fields":{"creator_twitter":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"content_id":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"creator_username":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"creator_instagram":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"post_comments":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"post_text":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"content_description":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"content_title":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"post_updated_at":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"creator_youtube":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"content_type":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"creator_name":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"creator_facebook":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"id":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}},"premium_plan":{"raw":{},"snippet":{"size":' + ENTRIES_PER_PAGE_STR + ',"fallback":true}}},"page":{"size":' + ENTRIES_PER_PAGE_STR + ',"current":' + str(page_n) + '}}'

                if self.service_url and self.service_access_key:
                    srch_res = _download_webpage(
                        url_or_request=self.service_url,
                        headers={'authorization': self.service_access_key},
                        data=POST_DATA.encode(enc),
                        encoding=enc,
                        video_id=_SEARCH_KEY,
                        note=f'Downloading search results (page {page_n}' + (f' of {pages_to_download}' if pages_to_download else '') + ')',
                        fatal=False)
                else:
                    write_debug(msg='gaining access')

                    # Try all possible combinations between service_urls and service_access_keys and see which one works.
                    # This should succeed on the first attempt, but no one knows for sure.
                    for service_url, service_access_key in itertools.product(service_urls, service_access_keys):
                        write_debug(msg=f'attempting to download 1st batch of search results from "{service_url}" using access key "{service_access_key}"')
                        srch_res = _download_webpage(
                            url_or_request=service_url,
                            headers={'authorization': service_access_key},
                            data=POST_DATA.encode(enc),
                            encoding=enc,
                            video_id=_SEARCH_KEY,
                            note=f'Downloading search results (page {page_n}' + (f' of {pages_to_download}' if pages_to_download else '') + ')',
                            fatal=False)

                        if type(srch_res) is str:
                            self.service_url = service_url
                            self.service_access_key = service_access_key
                            write_debug(msg='download succeeded, access gained')
                            break
                        else:
                            write_debug(msg='access denied. Still trying...')
                    else:
                        raise ExtractorError(msg='access denied', expected=False)

                for (ind, content) in enumerate(try_get(srch_res, lambda x: json_loads(x)['results']), start=1):
                    content_type = try_get(content, lambda x: x['content_type']['raw'])

                    if content_type in ('video', 'audio'):
                        video_url = try_get(content, lambda x: f'{BASE_URL}post/{int(x["id"]["raw"])}')
                        if video_url is None:
                            write_debug(msg=f'video/audio: could not process content entry: {content}')
                    elif content_type in ('stream', 'dead_stream'):
                        video_url = try_get(content, lambda x: f'{BASE_URL}stream/{int(x["content_id"]["raw"])}')
                        if video_url is None:
                            write_debug(msg=f'stream/dead_stream: could not process content entry: {content}')
                    elif content_type == 'stack':
                        video_url = try_get(content, lambda x: f'{BASE_URL}stack/{int(x["content_id"]["raw"])}')
                        if video_url is None:
                            write_debug(msg=f'stack: could not process content entry: {content}')
                    elif content_type == 'article':
                        video_url = try_get(content, lambda x: f'{BASE_URL}article/{int(x["content_id"]["raw"])}')
                        if video_url is None:
                            write_debug(msg=f'article: could not process content entry: {content}')
                    elif content_type == 'ranking':
                        video_url = try_get(content, lambda x: f'{BASE_URL}ranking/{int(x["content_id"]["raw"])}')
                        if video_url is None:
                            write_debug(msg=f'ranking: could not process content entry: {content}')
                    else:
                        video_url = None

                    if video_url:
                        yield url_result(video_url)

                        result_counter = result_counter + 1

                        if result_counter >= n_results:
                            return
                    else:
                        report_warning('skipping unsupported content type' + ('' if content_type is None else f': {content_type}') + '. Use --verbose to learn more')
                        write_debug(f'could not process content entry: {content}')

                # This is a safety feature. It'll have no effect 99% of the time:
                if page_n * ENTRIES_PER_PAGE >= max(2 * n_results, 100):
                    return

        return self.playlist_result(
            entries=dnl_video_meta_data_incrementally(query, n_results),
            playlist_id=query)

    def _get_access_credentials(self):
        import re

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
        for m in try_get(starting_wp_content, lambda x: re.finditer(r'<script\s+[^>]*?src\s*=\s*"(?P<path>/static/js/[^">]*)"[^>]*>', x)) or []:
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
        for m in re.finditer(r'(REACT_APP_SEARCH_KEY\s*:\s*"(?P<key>[^"]*)")|(REACT_APP_ENDPOINT_BASE\s*:\s*"(?P<url>[^"]*)")', js):
            if m.group('url'):
                service_urls.append(m.group('url') + SERVICE_URL_PATH)
            elif m.group('key'):
                services_access_keys.append('Bearer ' + m.group('key'))

        return (service_urls, services_access_keys)
