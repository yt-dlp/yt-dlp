# coding: utf-8
from .common import InfoExtractor
from ..utils import (
    unified_timestamp,
    try_get,
    float_or_none,
    url_or_none
)


# Rokfin treats each video as either a stream or a "post". Streams include active
# and pending live streams and their recordings. Pre-made videos are called "posts".


<<<<<<< HEAD
class RokfinSingleVideoIE(InfoExtractor):
=======
class RokfinIE(InfoExtractor):
>>>>>>> 33fe0177a (New field: channel_url; code refactored)
    _META_DATA_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/'
    _RECOMMENDED_VIDEO_BASE_URL = 'https://rokfin.com/'
    _CHANNEL_BASE_URL = 'https://rokfin.com/'


<<<<<<< HEAD
class RokfinPostIE(RokfinSingleVideoIE):
=======
class RokfinPostIE(RokfinIE):
>>>>>>> 33fe0177a (New field: channel_url; code refactored)
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
<<<<<<< HEAD
        downloaded_json = self._download_json(url_or_request=self._META_DATA_BASE_URL + video_id, video_id=video_id, note='Downloading video metadata', fatal=False)
=======
        downloaded_json = self._download_json(url_or_request=self._META_DATA_BASE_URL + video_id, video_id=video_id, note='Downloading video metadata')
>>>>>>> 33fe0177a (New field: channel_url; code refactored)

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
        m3u8_url = try_get(content_subdict, lambda x: url_or_none(x['contentUrl']))
        availability = try_get(self, lambda x: videoAvailability(x, downloaded_json))

        if m3u8_url:
            frmts = self._extract_m3u8_formats(m3u8_url=m3u8_url, video_id=video_id, fatal=False)
            self._sort_formats(frmts)
        else:
            frmts = None

<<<<<<< HEAD
            if availability == 'premium_only':
                # The video is premium only.
                self.raise_no_formats(msg='downloading premium content is unsupported', expected=True)
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
            'url': m3u8_url,
            'title': try_get(content_subdict, lambda x: x('contentTitle')),
            'webpage_url': self._RECOMMENDED_VIDEO_BASE_URL + video_id,
            'manifest_url': m3u8_url,
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
=======
            downloaded_json = downloaded_json.get
            created_by = try_get(downloaded_json, lambda x: x('createdBy')).get
            upload_date_time = try_get(downloaded_json, lambda x: x('creationDateTime'))
            channel_name = try_get(created_by, lambda x: x('name'))

            return {
                'id': video_id,
                'url': m3u8_url,
                'title': content_subdict.get('contentTitle'),
                'webpage_url': self._RECOMMENDED_VIDEO_BASE_URL + video_id,
                'manifest_url': m3u8_url,
                'is_live': False,
                'was_live': False,
                'live_status': 'not_live',
                'duration': float_or_none(content_subdict.get('duration')),
                'thumbnail': content_subdict.get('thumbnailUrl1'),
                'description': content_subdict.get('contentDescription'),
                'like_count': downloaded_json('likeCount'),
                'dislike_count': downloaded_json('dislikeCount'),
                'comment_count': downloaded_json('numComments'),
                'availability': availability,
                'creator': channel_name,
                'channel_id': try_get(created_by, lambda x: x('id')),
                'channel': channel_name,
                'channel_url': try_get(created_by, lambda x: self._CHANNEL_BASE_URL + x('username')),
                'timestamp': unified_timestamp(upload_date_time),
                'upload_date': unified_strdate(upload_date_time),
                'tags': [str(tag) for tag in try_get(downloaded_json, lambda x: x('tags')) or []],
                'formats': frmts,
                '__post_extractor': self.extract_comments(video_id=video_id)
            }
>>>>>>> 33fe0177a (New field: channel_url; code refactored)

    def _get_comments(self, video_id):
        import itertools

        _COMMENTS_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/comment'
        _COMMENTS_PER_REQUEST = 50  # 50 is the maximum Rokfin permits per request.

        def dnl_comments_incrementally(base_url, video_id, comments_per_page):
            pagesTotal = None

            for page_n in itertools.count(0):
                raw_comments = self._download_json(
                    url_or_request=f'{base_url}?postId={video_id[5:]}&page={page_n}&size={comments_per_page}',
                    video_id=video_id,
                    note=f'Downloading viewer comments (page {page_n + 1}' + (f' of {pagesTotal}' if pagesTotal else '') + ')',
                    fatal=False)

                comments = try_get(raw_comments, lambda x: x['content'])
                pagesTotal = try_get(raw_comments, lambda x: x['totalPages'])

                if comments:
                    yield comments

                if try_get(raw_comments, lambda x: x['last'] is True) or try_get(raw_comments, lambda x: page_n >= pagesTotal):
                    return

        for page_of_comments in dnl_comments_incrementally(_COMMENTS_BASE_URL, video_id, _COMMENTS_PER_REQUEST):
            for comment in page_of_comments:
<<<<<<< HEAD
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
=======
                yield {
                    'text': comment['comment'],
                    'author': comment['name'],
                    'id': comment['commentId'],
                    'author_id': comment['userId'],
                    'parent': 'root',
                    'like_count': comment['numLikes'],
                    'dislike_count': comment['numDislikes'],
                    'timestamp': try_get(comment, lambda x: unified_timestamp(x['postedAt']))
                }


class RokfinStreamIE(RokfinIE):
>>>>>>> 33fe0177a (New field: channel_url; code refactored)
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
<<<<<<< HEAD
        downloaded_json = self._download_json(url_or_request=self._META_DATA_BASE_URL + video_id, video_id=video_id, note='Downloading video metadata', fatal=False)
        m3u8_url = try_get(downloaded_json, lambda x: url_or_none(x['url']))
=======
        downloaded_json = self._download_json(url_or_request=self._META_DATA_BASE_URL + video_id, video_id=video_id, note='Downloading video metadata')

        m3u8_url = downloaded_json['url']

>>>>>>> 33fe0177a (New field: channel_url; code refactored)
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
                    + datetime.datetime.strftime(stream_scheduled_for, '%Y-%m-%dT%H:%M:%S' + ' (YYYY-MM-DD, 24H clock, GMT)'),
                    expected=True)

            if availability == 'premium_only':
                # The stream is premium only.
                self.raise_no_formats(msg='downloading premium content is unsupported', expected=True)

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
            mediaType = try_get(content, lambda x: x['mediaType'])

            if mediaType in ('video', 'audio'):
                video_url = try_get(content, lambda x: video_base_url + f'post/{x["id"]}')
                if video_url is None:
                    write_debug(msg=f'video: could not process content entry: {content}')
            elif mediaType in ('stream', 'dead_stream'):
                video_url = try_get(content, lambda x: video_base_url + f'stream/{x["mediaId"]}')
                if video_url is None:
                    write_debug(f'stream/dead_stream: could not process content entry: {content}')
            elif mediaType == 'stack':
                video_url = try_get(content, lambda x: video_base_url + f'stack/{x["mediaId"]}')
                if video_url is None:
                    write_debug(msg=f'stack: could not process content entry: {content}')
            elif mediaType == 'article':
                video_url = try_get(content, lambda x: video_base_url + f'article/{x["mediaId"]}')
                if video_url is None:
                    write_debug(msg=f'article: could not process content entry: {content}')
            else:
                video_url = None
                report_warning('skipping unsupported media type' + ('' if mediaType is None else f': {mediaType}') + '. Use --verbose to learn more')
                write_debug(msg=f'could not process content entry: {content}')

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
        _META_DATA_BASE_URL = 'https://prod-api-v2.production.rokfin.com/api/v2/public/user/'
        _RECOMMENDED_CHANNEL_BASE_URL = 'https://rokfin.com/'

        def dnl_video_meta_data_incrementally(pagesz, channel_id):
            _VIDEO_BASE_URL = 'https://rokfin.com/'

            pagesTotal = None

            for page_n in itertools.count(0):
                downloaded_json = self._download_json(url_or_request=f'{_META_DATA_BASE_URL}{channel_id}/posts?page={page_n}&size={pagesz}', video_id=channel_id, note=f'Downloading video metadata (page {page_n + 1}' + (f' of {pagesTotal}' if pagesTotal else '') + ')', fatal=False)

                pagesTotal = try_get(downloaded_json, lambda x: x['totalPages'])
                yield from self._get_video_data(json_data=downloaded_json, video_base_url=_VIDEO_BASE_URL)

                if try_get(downloaded_json, lambda x: x['last'] is True) or try_get(downloaded_json, lambda x: page_n >= pagesTotal):
                    return []

        channel_id = self._match_id(url_from_user)
        channel_info = self._download_json(url_or_request=_META_DATA_BASE_URL + channel_id, video_id=channel_id, note='Downloading channel info', fatal=False)

<<<<<<< HEAD
        return self.playlist_result(
            entries=dnl_video_meta_data_incrementally(pagesz=_ENTRIES_PER_REQUEST, channel_id=channel_id),
            playlist_id=try_get(channel_info, lambda x: x['id']),
            playlist_description=try_get(channel_info, lambda x: x['description']),
            webpage_url=_RECOMMENDED_CHANNEL_BASE_URL + channel_id)
=======
            created_by = downloaded_json('creator').get
            stream_ended_at_timestamp = try_get(stream_ended_at, lambda x: x.timestamp()) if include_time_fields else None
            channel_name = try_get(created_by, lambda x: x('name'))

            return {
                'id': video_id,
                'url': m3u8_url,
                'title': downloaded_json('title'),
                'webpage_url': self._RECOMMENDED_VIDEO_BASE_URL + video_id,
                'manifest_url': m3u8_url,
                'thumbnail': downloaded_json('thumbnail'),
                'description': downloaded_json('description'),
                'like_count': downloaded_json('likeCount'),
                'dislike_count': downloaded_json('dislikeCount'),
                'creator': channel_name,
                'channel_id': try_get(created_by, lambda x: x('id')),
                'uploader_id': try_get(created_by, lambda x: x('id')),
                'channel': channel_name,
                'channel_url': try_get(created_by, lambda x: self._CHANNEL_BASE_URL + x('username')),
                'availability': availability,
                'tags': [str(tag) for tag in try_get(downloaded_json, lambda x: x('tags')) or []],
                'is_live': stream_ended_at is None,
                'was_live': True if stream_ended_at else None,
                'live_status': 'not_live' if stream_ended_at else 'is_live',
                'start_time': stream_started_at,
                'duration': duration(stream_started_at, stream_ended_at),
                'timestamp': stream_ended_at_timestamp,
                'release_timestamp': stream_ended_at_timestamp,
                'release_date': stream_ended_at.strftime('%Y%m%d'),
                'formats': frmts
            }
>>>>>>> 33fe0177a (New field: channel_url; code refactored)
