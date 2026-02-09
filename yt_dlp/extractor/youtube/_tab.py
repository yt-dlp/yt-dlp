import functools
import itertools
import re
import shlex
import urllib.parse

from ._base import BadgeType, YoutubeBaseInfoExtractor
from ._video import YoutubeIE
from ...networking.exceptions import HTTPError, network_exceptions
from ...utils import (
    NO_DEFAULT,
    ExtractorError,
    UserNotLive,
    bug_reports_message,
    format_field,
    get_first,
    int_or_none,
    parse_count,
    parse_duration,
    parse_qs,
    smuggle_url,
    str_to_int,
    strftime_or_none,
    traverse_obj,
    try_get,
    unsmuggle_url,
    update_url_query,
    url_or_none,
    urljoin,
    variadic,
)


class YoutubeTabBaseInfoExtractor(YoutubeBaseInfoExtractor):
    @staticmethod
    def passthrough_smuggled_data(func):
        def _smuggle(info, smuggled_data):
            if info.get('_type') not in ('url', 'url_transparent'):
                return info
            if smuggled_data.get('is_music_url'):
                parsed_url = urllib.parse.urlparse(info['url'])
                if parsed_url.netloc in ('www.youtube.com', 'music.youtube.com'):
                    smuggled_data.pop('is_music_url')
                    info['url'] = urllib.parse.urlunparse(parsed_url._replace(netloc='music.youtube.com'))
            if smuggled_data:
                info['url'] = smuggle_url(info['url'], smuggled_data)
            return info

        @functools.wraps(func)
        def wrapper(self, url):
            url, smuggled_data = unsmuggle_url(url, {})
            if self.is_music_url(url):
                smuggled_data['is_music_url'] = True
            info_dict = func(self, url, smuggled_data)
            if smuggled_data:
                _smuggle(info_dict, smuggled_data)
                if info_dict.get('entries'):
                    info_dict['entries'] = (_smuggle(i, smuggled_data.copy()) for i in info_dict['entries'])
            return info_dict
        return wrapper

    @staticmethod
    def _extract_basic_item_renderer(item):
        # Modified from _extract_grid_item_renderer
        known_basic_renderers = (
            'playlistRenderer', 'videoRenderer', 'channelRenderer', 'showRenderer', 'reelItemRenderer',
        )
        for key, renderer in item.items():
            if not isinstance(renderer, dict):
                continue
            elif key in known_basic_renderers:
                return renderer
            elif key.startswith('grid') and key.endswith('Renderer'):
                return renderer

    def _extract_video(self, renderer):
        video_id = renderer.get('videoId')

        reel_header_renderer = traverse_obj(renderer, (
            'navigationEndpoint', 'reelWatchEndpoint', 'overlay', 'reelPlayerOverlayRenderer',
            'reelPlayerHeaderSupportedRenderers', 'reelPlayerHeaderRenderer'))

        title = self._get_text(renderer, 'title', 'headline') or self._get_text(reel_header_renderer, 'reelTitleText')
        description = self._get_text(renderer, 'descriptionSnippet')

        duration = int_or_none(renderer.get('lengthSeconds'))
        if duration is None:
            duration = parse_duration(self._get_text(
                renderer, 'lengthText', ('thumbnailOverlays', ..., 'thumbnailOverlayTimeStatusRenderer', 'text')))
        if duration is None:
            # XXX: should write a parser to be more general to support more cases (e.g. shorts in shorts tab)
            duration = parse_duration(self._search_regex(
                r'(?i)(ago)(?!.*\1)\s+(?P<duration>[a-z0-9 ,]+?)(?:\s+[\d,]+\s+views)?(?:\s+-\s+play\s+short)?$',
                traverse_obj(renderer, ('title', 'accessibility', 'accessibilityData', 'label'), default='', expected_type=str),
                video_id, default=None, group='duration'))

        channel_id = traverse_obj(
            renderer, ('shortBylineText', 'runs', ..., 'navigationEndpoint', 'browseEndpoint', 'browseId'),
            expected_type=str, get_all=False)
        if not channel_id:
            channel_id = traverse_obj(reel_header_renderer, ('channelNavigationEndpoint', 'browseEndpoint', 'browseId'))

        channel_id = self.ucid_or_none(channel_id)

        overlay_style = traverse_obj(
            renderer, ('thumbnailOverlays', ..., 'thumbnailOverlayTimeStatusRenderer', 'style'),
            get_all=False, expected_type=str)
        badges = self._extract_badges(traverse_obj(renderer, 'badges'))
        owner_badges = self._extract_badges(traverse_obj(renderer, 'ownerBadges'))
        navigation_url = urljoin('https://www.youtube.com/', traverse_obj(
            renderer, ('navigationEndpoint', 'commandMetadata', 'webCommandMetadata', 'url'),
            expected_type=str)) or ''
        url = f'https://www.youtube.com/watch?v={video_id}'
        if overlay_style == 'SHORTS' or '/shorts/' in navigation_url:
            url = f'https://www.youtube.com/shorts/{video_id}'

        time_text = (self._get_text(renderer, 'publishedTimeText', 'videoInfo')
                     or self._get_text(reel_header_renderer, 'timestampText') or '')
        scheduled_timestamp = str_to_int(traverse_obj(renderer, ('upcomingEventData', 'startTime'), get_all=False))

        live_status = (
            'is_upcoming' if scheduled_timestamp is not None
            else 'was_live' if 'streamed' in time_text.lower()
            else 'is_live' if overlay_style == 'LIVE' or self._has_badge(badges, BadgeType.LIVE_NOW)
            else None)

        # videoInfo is a string like '50K views • 10 years ago'.
        view_count_text = self._get_text(renderer, 'viewCountText', 'shortViewCountText', 'videoInfo') or ''
        view_count = (0 if 'no views' in view_count_text.lower()
                      else self._get_count({'simpleText': view_count_text}))
        view_count_field = 'concurrent_view_count' if live_status in ('is_live', 'is_upcoming') else 'view_count'

        channel = (self._get_text(renderer, 'ownerText', 'shortBylineText')
                   or self._get_text(reel_header_renderer, 'channelTitleText'))

        channel_handle = traverse_obj(renderer, (
            'shortBylineText', 'runs', ..., 'navigationEndpoint',
            (('commandMetadata', 'webCommandMetadata', 'url'), ('browseEndpoint', 'canonicalBaseUrl'))),
            expected_type=self.handle_from_url, get_all=False)
        return {
            '_type': 'url',
            'ie_key': YoutubeIE.ie_key(),
            'id': video_id,
            'url': url,
            'title': title,
            'description': description,
            'duration': duration,
            'channel_id': channel_id,
            'channel': channel,
            'channel_url': f'https://www.youtube.com/channel/{channel_id}' if channel_id else None,
            'uploader': channel,
            'uploader_id': channel_handle,
            'uploader_url': format_field(channel_handle, None, 'https://www.youtube.com/%s', default=None),
            'thumbnails': self._extract_thumbnails(renderer, 'thumbnail'),
            'timestamp': (self._parse_time_text(time_text)
                          if self._configuration_arg('approximate_date', ie_key=YoutubeTabIE)
                          else None),
            'release_timestamp': scheduled_timestamp,
            'availability':
                'public' if self._has_badge(badges, BadgeType.AVAILABILITY_PUBLIC)
                else self._availability(
                    is_private=self._has_badge(badges, BadgeType.AVAILABILITY_PRIVATE) or None,
                    needs_premium=self._has_badge(badges, BadgeType.AVAILABILITY_PREMIUM) or None,
                    needs_subscription=self._has_badge(badges, BadgeType.AVAILABILITY_SUBSCRIPTION) or None,
                    is_unlisted=self._has_badge(badges, BadgeType.AVAILABILITY_UNLISTED) or None),
            view_count_field: view_count,
            'live_status': live_status,
            'channel_is_verified': True if self._has_badge(owner_badges, BadgeType.VERIFIED) else None,
        }

    def _extract_channel_renderer(self, renderer):
        channel_id = self.ucid_or_none(renderer['channelId'])
        title = self._get_text(renderer, 'title')
        channel_url = format_field(channel_id, None, 'https://www.youtube.com/channel/%s', default=None)
        channel_handle = self.handle_from_url(
            traverse_obj(renderer, (
                'navigationEndpoint', (('commandMetadata', 'webCommandMetadata', 'url'),
                                       ('browseEndpoint', 'canonicalBaseUrl')),
                {str}), get_all=False))
        if not channel_handle:
            # As of 2023-06-01, YouTube sets subscriberCountText to the handle in search
            channel_handle = self.handle_or_none(self._get_text(renderer, 'subscriberCountText'))
        return {
            '_type': 'url',
            'url': channel_url,
            'id': channel_id,
            'ie_key': YoutubeTabIE.ie_key(),
            'channel': title,
            'uploader': title,
            'channel_id': channel_id,
            'channel_url': channel_url,
            'title': title,
            'uploader_id': channel_handle,
            'uploader_url': format_field(channel_handle, None, 'https://www.youtube.com/%s', default=None),
            # See above. YouTube sets videoCountText to the subscriber text in search channel renderers.
            # However, in feed/channels this is set correctly to the subscriber count
            'channel_follower_count': traverse_obj(
                renderer, 'subscriberCountText', 'videoCountText', expected_type=self._get_count),
            'thumbnails': self._extract_thumbnails(renderer, 'thumbnail'),
            'playlist_count': (
                # videoCountText may be the subscriber count
                self._get_count(renderer, 'videoCountText')
                if self._get_count(renderer, 'subscriberCountText') is not None else None),
            'description': self._get_text(renderer, 'descriptionSnippet'),
            'channel_is_verified': True if self._has_badge(
                self._extract_badges(traverse_obj(renderer, 'ownerBadges')), BadgeType.VERIFIED) else None,
        }

    def _grid_entries(self, grid_renderer):
        for item in grid_renderer['items']:
            if not isinstance(item, dict):
                continue
            if lockup_view_model := traverse_obj(item, ('lockupViewModel', {dict})):
                if entry := self._extract_lockup_view_model(lockup_view_model):
                    yield entry
                continue
            renderer = self._extract_basic_item_renderer(item)
            if not isinstance(renderer, dict):
                continue
            title = self._get_text(renderer, 'title')

            # playlist
            playlist_id = renderer.get('playlistId')
            if playlist_id:
                yield self.url_result(
                    f'https://www.youtube.com/playlist?list={playlist_id}',
                    ie=YoutubeTabIE.ie_key(), video_id=playlist_id,
                    video_title=title)
                continue
            # video
            video_id = renderer.get('videoId')
            if video_id:
                yield self._extract_video(renderer)
                continue
            # channel
            channel_id = renderer.get('channelId')
            if channel_id:
                yield self._extract_channel_renderer(renderer)
                continue
            # generic endpoint URL support
            ep_url = urljoin('https://www.youtube.com/', try_get(
                renderer, lambda x: x['navigationEndpoint']['commandMetadata']['webCommandMetadata']['url'],
                str))
            if ep_url:

                for ie in (YoutubeTabIE, YoutubePlaylistIE, YoutubeIE):
                    if ie.suitable(ep_url):
                        yield self.url_result(
                            ep_url, ie=ie.ie_key(), video_id=ie._match_id(ep_url), video_title=title)
                        break

    def _music_reponsive_list_entry(self, renderer):
        video_id = traverse_obj(renderer, ('playlistItemData', 'videoId'))
        if video_id:
            title = traverse_obj(renderer, (
                'flexColumns', 0, 'musicResponsiveListItemFlexColumnRenderer',
                'text', 'runs', 0, 'text'))
            return self.url_result(f'https://music.youtube.com/watch?v={video_id}',
                                   ie=YoutubeIE.ie_key(), video_id=video_id, title=title)
        playlist_id = traverse_obj(renderer, ('navigationEndpoint', 'watchEndpoint', 'playlistId'))
        if playlist_id:
            video_id = traverse_obj(renderer, ('navigationEndpoint', 'watchEndpoint', 'videoId'))
            if video_id:
                return self.url_result(f'https://music.youtube.com/watch?v={video_id}&list={playlist_id}',
                                       ie=YoutubeTabIE.ie_key(), video_id=playlist_id)
            return self.url_result(f'https://music.youtube.com/playlist?list={playlist_id}',
                                   ie=YoutubeTabIE.ie_key(), video_id=playlist_id)
        browse_id = traverse_obj(renderer, ('navigationEndpoint', 'browseEndpoint', 'browseId'))
        if browse_id:
            return self.url_result(f'https://music.youtube.com/browse/{browse_id}',
                                   ie=YoutubeTabIE.ie_key(), video_id=browse_id)

    def _shelf_entries_from_content(self, shelf_renderer):
        content = shelf_renderer.get('content')
        if not isinstance(content, dict):
            return
        renderer = content.get('gridRenderer') or content.get('expandedShelfContentsRenderer')
        if renderer:
            # TODO: add support for nested playlists so each shelf is processed
            # as separate playlist
            # TODO: this includes only first N items
            yield from self._grid_entries(renderer)
        renderer = content.get('horizontalListRenderer')
        if renderer:
            # TODO: handle case
            pass

    def _shelf_entries(self, shelf_renderer, skip_channels=False):
        ep = try_get(
            shelf_renderer, lambda x: x['endpoint']['commandMetadata']['webCommandMetadata']['url'],
            str)
        shelf_url = urljoin('https://www.youtube.com', ep)
        if shelf_url:
            # Skipping links to another channels, note that checking for
            # endpoint.commandMetadata.webCommandMetadata.webPageTypwebPageType == WEB_PAGE_TYPE_CHANNEL
            # will not work
            if skip_channels and '/channels?' in shelf_url:
                return
            title = self._get_text(shelf_renderer, 'title')
            yield self.url_result(shelf_url, video_title=title)
        # Shelf may not contain shelf URL, fallback to extraction from content
        yield from self._shelf_entries_from_content(shelf_renderer)

    def _playlist_entries(self, video_list_renderer):
        for content in video_list_renderer['contents']:
            if not isinstance(content, dict):
                continue
            renderer = content.get('playlistVideoRenderer') or content.get('playlistPanelVideoRenderer')
            if not isinstance(renderer, dict):
                continue
            video_id = renderer.get('videoId')
            if not video_id:
                continue
            yield self._extract_video(renderer)

    def _extract_lockup_view_model(self, view_model):
        content_id = view_model.get('contentId')
        if not content_id:
            return

        content_type = view_model.get('contentType')
        if content_type == 'LOCKUP_CONTENT_TYPE_VIDEO':
            ie = YoutubeIE
            url = f'https://www.youtube.com/watch?v={content_id}'
            thumb_keys = (None,)
        elif content_type in ('LOCKUP_CONTENT_TYPE_PLAYLIST', 'LOCKUP_CONTENT_TYPE_PODCAST'):
            ie = YoutubeTabIE
            url = f'https://www.youtube.com/playlist?list={content_id}'
            thumb_keys = ('collectionThumbnailViewModel', 'primaryThumbnail')
        else:
            self.report_warning(
                f'Unsupported lockup view model content type "{content_type}"{bug_reports_message()}',
                only_once=True)
            return

        return self.url_result(
            url, ie, content_id,
            title=traverse_obj(view_model, (
                'metadata', 'lockupMetadataViewModel', 'title', 'content', {str})),
            thumbnails=self._extract_thumbnails(view_model, (
                'contentImage', *thumb_keys, 'thumbnailViewModel', 'image'), final_key='sources'),
            duration=traverse_obj(view_model, (
                'contentImage', 'thumbnailViewModel', 'overlays', ...,
                (('thumbnailBottomOverlayViewModel', 'badges'), ('thumbnailOverlayBadgeViewModel', 'thumbnailBadges')),
                ..., 'thumbnailBadgeViewModel', 'text', {parse_duration}, any)),
            timestamp=(traverse_obj(view_model, (
                'metadata', 'lockupMetadataViewModel', 'metadata', 'contentMetadataViewModel', 'metadataRows',
                ..., 'metadataParts', ..., 'text', 'content', {lambda t: self._parse_time_text(t, report_failure=False)}, any))
                if self._configuration_arg('approximate_date', ie_key=YoutubeTabIE) else None))

    def _rich_entries(self, rich_grid_renderer):
        if lockup_view_model := traverse_obj(rich_grid_renderer, ('content', 'lockupViewModel', {dict})):
            if entry := self._extract_lockup_view_model(lockup_view_model):
                yield entry
            return
        renderer = traverse_obj(
            rich_grid_renderer,
            ('content', ('videoRenderer', 'reelItemRenderer', 'playlistRenderer', 'shortsLockupViewModel'), any)) or {}
        video_id = renderer.get('videoId')
        if video_id:
            yield self._extract_video(renderer)
            return
        playlist_id = renderer.get('playlistId')
        if playlist_id:
            yield self.url_result(
                f'https://www.youtube.com/playlist?list={playlist_id}',
                ie=YoutubeTabIE.ie_key(), video_id=playlist_id,
                video_title=self._get_text(renderer, 'title'))
            return
        # shortsLockupViewModel extraction
        entity_id = renderer.get('entityId')
        if entity_id:
            video_id = traverse_obj(renderer, ('onTap', 'innertubeCommand', 'reelWatchEndpoint', 'videoId', {str}))
            if not video_id:
                return
            yield self.url_result(
                f'https://www.youtube.com/shorts/{video_id}',
                ie=YoutubeIE, video_id=video_id,
                **traverse_obj(renderer, {
                    'title': ((
                        ('overlayMetadata', 'primaryText', 'content', {str}),
                        ('accessibilityText', {lambda x: re.fullmatch(r'(.+), (?:[\d,.]+(?:[KM]| million)?|No) views? - play Short', x)}, 1)), any),
                    'view_count': ('overlayMetadata', 'secondaryText', 'content', {parse_count}),
                }),
                thumbnails=self._extract_thumbnails(
                    renderer, ('thumbnailViewModel', 'thumbnailViewModel', 'image'), final_key='sources'))
            return

    def _video_entry(self, video_renderer):
        video_id = video_renderer.get('videoId')
        if video_id:
            return self._extract_video(video_renderer)

    def _hashtag_tile_entry(self, hashtag_tile_renderer):
        url = urljoin('https://youtube.com', traverse_obj(
            hashtag_tile_renderer, ('onTapCommand', 'commandMetadata', 'webCommandMetadata', 'url')))
        if url:
            return self.url_result(
                url, ie=YoutubeTabIE.ie_key(), title=self._get_text(hashtag_tile_renderer, 'hashtag'))

    def _post_thread_entries(self, post_thread_renderer):
        post_renderer = try_get(
            post_thread_renderer, lambda x: x['post']['backstagePostRenderer'], dict)
        if not post_renderer:
            return
        # video attachment
        video_renderer = try_get(
            post_renderer, lambda x: x['backstageAttachment']['videoRenderer'], dict) or {}
        video_id = video_renderer.get('videoId')
        if video_id:
            entry = self._extract_video(video_renderer)
            if entry:
                yield entry
        # playlist attachment
        playlist_id = try_get(
            post_renderer, lambda x: x['backstageAttachment']['playlistRenderer']['playlistId'], str)
        if playlist_id:
            yield self.url_result(
                f'https://www.youtube.com/playlist?list={playlist_id}',
                ie=YoutubeTabIE.ie_key(), video_id=playlist_id)
        # inline video links
        runs = try_get(post_renderer, lambda x: x['contentText']['runs'], list) or []
        for run in runs:
            if not isinstance(run, dict):
                continue
            ep_url = try_get(
                run, lambda x: x['navigationEndpoint']['urlEndpoint']['url'], str)
            if not ep_url:
                continue
            if not YoutubeIE.suitable(ep_url):
                continue
            ep_video_id = YoutubeIE._match_id(ep_url)
            if video_id == ep_video_id:
                continue
            yield self.url_result(ep_url, ie=YoutubeIE.ie_key(), video_id=ep_video_id)

    def _post_thread_continuation_entries(self, post_thread_continuation):
        contents = post_thread_continuation.get('contents')
        if not isinstance(contents, list):
            return
        for content in contents:
            renderer = content.get('backstagePostThreadRenderer')
            if isinstance(renderer, dict):
                yield from self._post_thread_entries(renderer)
                continue
            renderer = content.get('videoRenderer')
            if isinstance(renderer, dict):
                yield self._video_entry(renderer)

    r''' # unused
    def _rich_grid_entries(self, contents):
        for content in contents:
            video_renderer = try_get(content, lambda x: x['richItemRenderer']['content']['videoRenderer'], dict)
            if video_renderer:
                entry = self._video_entry(video_renderer)
                if entry:
                    yield entry
    '''

    def _report_history_entries(self, renderer):
        for url in traverse_obj(renderer, (
                'rows', ..., 'reportHistoryTableRowRenderer', 'cells', ...,
                'reportHistoryTableCellRenderer', 'cell', 'reportHistoryTableTextCellRenderer', 'text', 'runs', ...,
                'navigationEndpoint', 'commandMetadata', 'webCommandMetadata', 'url')):
            yield self.url_result(urljoin('https://www.youtube.com', url), YoutubeIE)

    def _extract_entries(self, parent_renderer, continuation_list):
        # continuation_list is modified in-place with continuation_list = [continuation_token]
        continuation_list[:] = [None]
        contents = try_get(parent_renderer, lambda x: x['contents'], list) or []
        for content in contents:
            if not isinstance(content, dict):
                continue
            is_renderer = traverse_obj(
                content, 'itemSectionRenderer', 'musicShelfRenderer', 'musicShelfContinuation',
                expected_type=dict)
            if not is_renderer:
                if content.get('richItemRenderer'):
                    for entry in self._rich_entries(content['richItemRenderer']):
                        yield entry
                    continuation_list[0] = self._extract_continuation(parent_renderer)
                elif content.get('reportHistorySectionRenderer'):  # https://www.youtube.com/reporthistory
                    table = traverse_obj(content, ('reportHistorySectionRenderer', 'table', 'tableRenderer'))
                    yield from self._report_history_entries(table)
                    continuation_list[0] = self._extract_continuation(table)
                continue

            isr_contents = try_get(is_renderer, lambda x: x['contents'], list) or []
            for isr_content in isr_contents:
                if not isinstance(isr_content, dict):
                    continue

                known_renderers = {
                    'playlistVideoListRenderer': self._playlist_entries,
                    'gridRenderer': self._grid_entries,
                    'reelShelfRenderer': self._grid_entries,
                    'shelfRenderer': self._shelf_entries,
                    'musicResponsiveListItemRenderer': lambda x: [self._music_reponsive_list_entry(x)],
                    'backstagePostThreadRenderer': self._post_thread_entries,
                    'videoRenderer': lambda x: [self._video_entry(x)],
                    'playlistRenderer': lambda x: self._grid_entries({'items': [{'playlistRenderer': x}]}),
                    'channelRenderer': lambda x: self._grid_entries({'items': [{'channelRenderer': x}]}),
                    'hashtagTileRenderer': lambda x: [self._hashtag_tile_entry(x)],
                    'richGridRenderer': lambda x: self._extract_entries(x, continuation_list),
                    'lockupViewModel': lambda x: [self._extract_lockup_view_model(x)],
                }
                for key, renderer in isr_content.items():
                    if key not in known_renderers:
                        continue
                    for entry in known_renderers[key](renderer):
                        if entry:
                            yield entry
                    continuation_list[0] = self._extract_continuation(renderer)
                    break

            if not continuation_list[0]:
                continuation_list[0] = self._extract_continuation(is_renderer)

        if not continuation_list[0]:
            continuation_list[0] = self._extract_continuation(parent_renderer)

    def _entries(self, tab, item_id, ytcfg, delegated_session_id, visitor_data):
        continuation_list = [None]
        extract_entries = lambda x: self._extract_entries(x, continuation_list)
        tab_content = try_get(tab, lambda x: x['content'], dict)
        if not tab_content:
            return
        parent_renderer = (
            try_get(tab_content, lambda x: x['sectionListRenderer'], dict)
            or try_get(tab_content, lambda x: x['richGridRenderer'], dict) or {})
        yield from extract_entries(parent_renderer)
        continuation = continuation_list[0]
        seen_continuations = set()
        for page_num in itertools.count(1):
            if not continuation:
                break
            continuation_token = continuation.get('continuation')
            if continuation_token is not None and continuation_token in seen_continuations:
                self.write_debug('Detected YouTube feed looping - assuming end of feed.')
                break
            seen_continuations.add(continuation_token)
            headers = self.generate_api_headers(
                ytcfg=ytcfg, delegated_session_id=delegated_session_id, visitor_data=visitor_data)
            response = self._extract_response(
                item_id=f'{item_id} page {page_num}',
                query=continuation, headers=headers, ytcfg=ytcfg,
                check_get_keys=(
                    'continuationContents', 'onResponseReceivedActions', 'onResponseReceivedEndpoints',
                    # Playlist recommendations may return with no data - ignore
                    ('responseContext', 'serviceTrackingParams', ..., 'params', ..., lambda k, v: k == 'key' and v == 'GetRecommendedMusicPlaylists_rid'),
                ))

            if not response:
                break

            continuation = None
            # Extracting updated visitor data is required to prevent an infinite extraction loop in some cases
            # See: https://github.com/ytdl-org/youtube-dl/issues/28702
            visitor_data = self._extract_visitor_data(response) or visitor_data

            known_renderers = {
                'videoRenderer': (self._grid_entries, 'items'),  # for membership tab
                'gridPlaylistRenderer': (self._grid_entries, 'items'),
                'gridVideoRenderer': (self._grid_entries, 'items'),
                'gridChannelRenderer': (self._grid_entries, 'items'),
                'playlistVideoRenderer': (self._playlist_entries, 'contents'),
                'itemSectionRenderer': (extract_entries, 'contents'),  # for feeds
                'richItemRenderer': (extract_entries, 'contents'),  # for hashtag
                'backstagePostThreadRenderer': (self._post_thread_continuation_entries, 'contents'),
                'reportHistoryTableRowRenderer': (self._report_history_entries, 'rows'),
                'playlistVideoListContinuation': (self._playlist_entries, None),
                'gridContinuation': (self._grid_entries, None),
                'itemSectionContinuation': (self._post_thread_continuation_entries, None),
                'sectionListContinuation': (extract_entries, None),  # for feeds
                'lockupViewModel': (self._grid_entries, 'items'),  # for playlists tab
            }

            continuation_items = traverse_obj(response, (
                ('onResponseReceivedActions', 'onResponseReceivedEndpoints'), ...,
                'appendContinuationItemsAction', 'continuationItems',
            ), 'continuationContents', get_all=False)
            continuation_item = traverse_obj(continuation_items, 0, None, expected_type=dict, default={})

            video_items_renderer = None
            for key in continuation_item:
                if key not in known_renderers:
                    continue
                func, parent_key = known_renderers[key]
                video_items_renderer = {parent_key: continuation_items} if parent_key else continuation_items
                continuation_list = [None]
                yield from func(video_items_renderer)
                continuation = continuation_list[0] or self._extract_continuation(video_items_renderer)

            # In the case only a continuation is returned, try to follow it.
            # We extract this after trying to extract non-continuation items as otherwise this
            # may be prioritized over other continuations.
            # see: https://github.com/yt-dlp/yt-dlp/issues/12933
            continuation = continuation or self._extract_continuation({'contents': [continuation_item]})

            if not continuation and not video_items_renderer:
                break

    @staticmethod
    def _extract_selected_tab(tabs, fatal=True):
        for tab_renderer in tabs:
            if tab_renderer.get('selected'):
                return tab_renderer
        if fatal:
            raise ExtractorError('Unable to find selected tab')

    @staticmethod
    def _extract_tab_renderers(response):
        return traverse_obj(
            response, ('contents', 'twoColumnBrowseResultsRenderer', 'tabs', ..., ('tabRenderer', 'expandableTabRenderer')), expected_type=dict)

    def _extract_from_tabs(self, item_id, ytcfg, data, tabs):
        metadata = self._extract_metadata_from_tabs(item_id, data)

        selected_tab = self._extract_selected_tab(tabs)
        metadata['title'] += format_field(selected_tab, 'title', ' - %s')
        metadata['title'] += format_field(selected_tab, 'expandedText', ' - %s')

        return self.playlist_result(
            self._entries(
                selected_tab, metadata['id'], ytcfg,
                self._extract_delegated_session_id(ytcfg, data),
                self._extract_visitor_data(data, ytcfg)),
            **metadata)

    def _extract_metadata_from_tabs(self, item_id, data):
        info = {'id': item_id}

        metadata_renderer = traverse_obj(data, ('metadata', 'channelMetadataRenderer'), expected_type=dict)
        if metadata_renderer:
            channel_id = traverse_obj(metadata_renderer, ('externalId', {self.ucid_or_none}),
                                      ('channelUrl', {self.ucid_from_url}))
            info.update({
                'channel': metadata_renderer.get('title'),
                'channel_id': channel_id,
            })
            if info['channel_id']:
                info['id'] = info['channel_id']
        else:
            metadata_renderer = traverse_obj(data, ('metadata', 'playlistMetadataRenderer'), expected_type=dict)

        # pageHeaderViewModel slow rollout began April 2024
        page_header_view_model = traverse_obj(data, (
            'header', 'pageHeaderRenderer', 'content', 'pageHeaderViewModel', {dict}))

        # We can get the uncropped banner/avatar by replacing the crop params with '=s0'
        # See: https://github.com/yt-dlp/yt-dlp/issues/2237#issuecomment-1013694714
        def _get_uncropped(url):
            return url_or_none((url or '').split('=')[0] + '=s0')

        avatar_thumbnails = self._extract_thumbnails(metadata_renderer, 'avatar')
        if avatar_thumbnails:
            uncropped_avatar = _get_uncropped(avatar_thumbnails[0]['url'])
            if uncropped_avatar:
                avatar_thumbnails.append({
                    'url': uncropped_avatar,
                    'id': 'avatar_uncropped',
                    'preference': 1,
                })

        channel_banners = (
            self._extract_thumbnails(data, ('header', ..., ('banner', 'mobileBanner', 'tvBanner')))
            or self._extract_thumbnails(
                page_header_view_model, ('banner', 'imageBannerViewModel', 'image'), final_key='sources'))
        for banner in channel_banners:
            banner['preference'] = -10

        if channel_banners:
            uncropped_banner = _get_uncropped(channel_banners[0]['url'])
            if uncropped_banner:
                channel_banners.append({
                    'url': uncropped_banner,
                    'id': 'banner_uncropped',
                    'preference': -5,
                })

        # Deprecated - remove primary_sidebar_renderer when layout discontinued
        primary_sidebar_renderer = self._extract_sidebar_info_renderer(data, 'playlistSidebarPrimaryInfoRenderer')
        playlist_header_renderer = traverse_obj(data, ('header', 'playlistHeaderRenderer'), expected_type=dict)

        primary_thumbnails = self._extract_thumbnails(
            primary_sidebar_renderer, ('thumbnailRenderer', ('playlistVideoThumbnailRenderer', 'playlistCustomThumbnailRenderer'), 'thumbnail'))
        playlist_thumbnails = self._extract_thumbnails(
            playlist_header_renderer, ('playlistHeaderBanner', 'heroPlaylistThumbnailRenderer', 'thumbnail'))

        info.update({
            'title': (traverse_obj(metadata_renderer, 'title')
                      or self._get_text(data, ('header', 'hashtagHeaderRenderer', 'hashtag'))
                      or info['id']),
            'availability': self._extract_availability(data),
            'channel_follower_count': (
                self._get_count(data, ('header', ..., 'subscriberCountText'))
                or traverse_obj(page_header_view_model, (
                    'metadata', 'contentMetadataViewModel', 'metadataRows', ..., 'metadataParts',
                    lambda _, v: 'subscribers' in v['text']['content'], 'text', 'content', {parse_count}, any))),
            'description': try_get(metadata_renderer, lambda x: x.get('description', '')),
            'tags': (traverse_obj(data, ('microformat', 'microformatDataRenderer', 'tags', ..., {str}))
                     or traverse_obj(metadata_renderer, ('keywords', {lambda x: x and shlex.split(x)}, ...))),
            'thumbnails': (primary_thumbnails or playlist_thumbnails) + avatar_thumbnails + channel_banners,
        })

        channel_handle = (
            traverse_obj(metadata_renderer, (('vanityChannelUrl', ('ownerUrls', ...)), {self.handle_from_url}), get_all=False)
            or traverse_obj(data, ('header', ..., 'channelHandleText', {self.handle_or_none}), get_all=False))

        if channel_handle:
            info.update({
                'uploader_id': channel_handle,
                'uploader_url': format_field(channel_handle, None, 'https://www.youtube.com/%s', default=None),
            })

        channel_badges = self._extract_badges(traverse_obj(data, ('header', ..., 'badges'), get_all=False))
        if self._has_badge(channel_badges, BadgeType.VERIFIED):
            info['channel_is_verified'] = True
        # Playlist stats is a text runs array containing [video count, view count, last updated].
        # last updated or (view count and last updated) may be missing.
        playlist_stats = get_first(
            (primary_sidebar_renderer, playlist_header_renderer), (('stats', 'briefStats', 'numVideosText'), ))

        last_updated_unix = self._parse_time_text(
            self._get_text(playlist_stats, 2)  # deprecated, remove when old layout discontinued
            or self._get_text(playlist_header_renderer, ('byline', 1, 'playlistBylineRenderer', 'text')))
        info['modified_date'] = strftime_or_none(last_updated_unix)

        info['view_count'] = self._get_count(playlist_stats, 1)
        if info['view_count'] is None:  # 0 is allowed
            info['view_count'] = self._get_count(playlist_header_renderer, 'viewCountText')
        if info['view_count'] is None:
            info['view_count'] = self._get_count(data, (
                'contents', 'twoColumnBrowseResultsRenderer', 'tabs', ..., 'tabRenderer', 'content', 'sectionListRenderer',
                'contents', ..., 'itemSectionRenderer', 'contents', ..., 'channelAboutFullMetadataRenderer', 'viewCountText'))

        info['playlist_count'] = self._get_count(playlist_stats, 0)
        if info['playlist_count'] is None:  # 0 is allowed
            info['playlist_count'] = self._get_count(playlist_header_renderer, ('byline', 0, 'playlistBylineRenderer', 'text'))

        if not info.get('channel_id'):
            owner = traverse_obj(playlist_header_renderer, 'ownerText')
            if not owner:  # Deprecated
                owner = traverse_obj(
                    self._extract_sidebar_info_renderer(data, 'playlistSidebarSecondaryInfoRenderer'),
                    ('videoOwner', 'videoOwnerRenderer', 'title'))
            owner_text = self._get_text(owner)
            browse_ep = traverse_obj(owner, ('runs', 0, 'navigationEndpoint', 'browseEndpoint')) or {}
            info.update({
                'channel': self._search_regex(r'^by (.+) and \d+ others?$', owner_text, 'uploader', default=owner_text),
                'channel_id': self.ucid_or_none(browse_ep.get('browseId')),
                'uploader_id': self.handle_from_url(urljoin('https://www.youtube.com', browse_ep.get('canonicalBaseUrl'))),
            })

        info.update({
            'uploader': info['channel'],
            'channel_url': format_field(info.get('channel_id'), None, 'https://www.youtube.com/channel/%s', default=None),
            'uploader_url': format_field(info.get('uploader_id'), None, 'https://www.youtube.com/%s', default=None),
        })

        return info

    def _extract_inline_playlist(self, playlist, playlist_id, data, ytcfg):
        first_id = last_id = response = None
        for page_num in itertools.count(1):
            videos = list(self._playlist_entries(playlist))
            if not videos:
                return
            start = next((i for i, v in enumerate(videos) if v['id'] == last_id), -1) + 1
            if start >= len(videos):
                return
            yield from videos[start:]
            first_id = first_id or videos[0]['id']
            last_id = videos[-1]['id']
            watch_endpoint = try_get(
                playlist, lambda x: x['contents'][-1]['playlistPanelVideoRenderer']['navigationEndpoint']['watchEndpoint'])
            headers = self.generate_api_headers(
                ytcfg=ytcfg, delegated_session_id=self._extract_delegated_session_id(ytcfg, data),
                visitor_data=self._extract_visitor_data(response, data, ytcfg))
            query = {
                'playlistId': playlist_id,
                'videoId': watch_endpoint.get('videoId') or last_id,
                'index': watch_endpoint.get('index') or len(videos),
                'params': watch_endpoint.get('params') or 'OAE%3D',
            }
            response = self._extract_response(
                item_id=f'{playlist_id} page {page_num}',
                query=query, ep='next', headers=headers, ytcfg=ytcfg,
                check_get_keys='contents',
            )
            playlist = try_get(
                response, lambda x: x['contents']['twoColumnWatchNextResults']['playlist']['playlist'], dict)

    def _extract_from_playlist(self, item_id, url, data, playlist, ytcfg):
        title = playlist.get('title') or try_get(
            data, lambda x: x['titleText']['simpleText'], str)
        playlist_id = playlist.get('playlistId') or item_id

        # Delegating everything except mix playlists to regular tab-based playlist URL
        playlist_url = urljoin(url, try_get(
            playlist, lambda x: x['endpoint']['commandMetadata']['webCommandMetadata']['url'],
            str))

        # Some playlists are unviewable but YouTube still provides a link to the (broken) playlist page [1]
        # [1] MLCT, RLTDwFCb4jeqaKWnciAYM-ZVHg
        is_known_unviewable = re.fullmatch(r'MLCT|RLTD[\w-]{22}', playlist_id)

        if playlist_url and playlist_url != url and not is_known_unviewable:
            return self.url_result(
                playlist_url, ie=YoutubeTabIE.ie_key(), video_id=playlist_id,
                video_title=title)

        return self.playlist_result(
            self._extract_inline_playlist(playlist, playlist_id, data, ytcfg),
            playlist_id=playlist_id, playlist_title=title)

    def _extract_availability(self, data):
        """
        Gets the availability of a given playlist/tab.
        Note: Unless YouTube tells us explicitly, we do not assume it is public
        @param data: response
        """
        sidebar_renderer = self._extract_sidebar_info_renderer(data, 'playlistSidebarPrimaryInfoRenderer') or {}
        playlist_header_renderer = traverse_obj(data, ('header', 'playlistHeaderRenderer')) or {}
        player_header_privacy = playlist_header_renderer.get('privacy')

        badges = self._extract_badges(traverse_obj(sidebar_renderer, 'badges'))

        # Personal playlists, when authenticated, have a dropdown visibility selector instead of a badge
        privacy_setting_icon = get_first(
            (playlist_header_renderer, sidebar_renderer),
            ('privacyForm', 'dropdownFormFieldRenderer', 'dropdown', 'dropdownRenderer', 'entries',
             lambda _, v: v['privacyDropdownItemRenderer']['isSelected'], 'privacyDropdownItemRenderer', 'icon', 'iconType'),
            expected_type=str)

        microformats_is_unlisted = traverse_obj(
            data, ('microformat', 'microformatDataRenderer', 'unlisted'), expected_type=bool)

        return (
            'public' if (
                self._has_badge(badges, BadgeType.AVAILABILITY_PUBLIC)
                or player_header_privacy == 'PUBLIC'
                or privacy_setting_icon == 'PRIVACY_PUBLIC')
            else self._availability(
                is_private=(
                    self._has_badge(badges, BadgeType.AVAILABILITY_PRIVATE)
                    or player_header_privacy == 'PRIVATE' if player_header_privacy is not None
                    else privacy_setting_icon == 'PRIVACY_PRIVATE' if privacy_setting_icon is not None else None),
                is_unlisted=(
                    self._has_badge(badges, BadgeType.AVAILABILITY_UNLISTED)
                    or player_header_privacy == 'UNLISTED' if player_header_privacy is not None
                    else privacy_setting_icon == 'PRIVACY_UNLISTED' if privacy_setting_icon is not None
                    else microformats_is_unlisted if microformats_is_unlisted is not None else None),
                needs_subscription=self._has_badge(badges, BadgeType.AVAILABILITY_SUBSCRIPTION) or None,
                needs_premium=self._has_badge(badges, BadgeType.AVAILABILITY_PREMIUM) or None,
                needs_auth=False))

    @staticmethod
    def _extract_sidebar_info_renderer(data, info_renderer, expected_type=dict):
        sidebar_renderer = try_get(
            data, lambda x: x['sidebar']['playlistSidebarRenderer']['items'], list) or []
        for item in sidebar_renderer:
            renderer = try_get(item, lambda x: x[info_renderer], expected_type)
            if renderer:
                return renderer

    def _reload_with_unavailable_videos(self, item_id, data, ytcfg):
        """
        Reload playlists with unavailable videos (e.g. private videos, region blocked, etc.)
        """
        is_playlist = bool(traverse_obj(
            data, ('metadata', 'playlistMetadataRenderer'), ('header', 'playlistHeaderRenderer')))
        if not is_playlist:
            return
        headers = self.generate_api_headers(
            ytcfg=ytcfg, delegated_session_id=self._extract_delegated_session_id(ytcfg, data),
            visitor_data=self._extract_visitor_data(data, ytcfg))
        query = {
            'params': 'wgYCCAA=',
            'browseId': f'VL{item_id}',
        }
        return self._extract_response(
            item_id=item_id, headers=headers, query=query,
            check_get_keys='contents', fatal=False, ytcfg=ytcfg,
            note='Redownloading playlist API JSON with unavailable videos')

    @functools.cached_property
    def skip_webpage(self):
        return 'webpage' in self._configuration_arg('skip', ie_key=YoutubeTabIE.ie_key())

    def _extract_webpage(self, url, item_id, fatal=True):
        webpage, data = None, None
        for retry in self.RetryManager(fatal=fatal):
            try:
                webpage = self._download_webpage(url, item_id, note='Downloading webpage')
                data = self.extract_yt_initial_data(item_id, webpage or '', fatal=fatal) or {}
            except ExtractorError as e:
                if isinstance(e.cause, network_exceptions):
                    if not isinstance(e.cause, HTTPError) or e.cause.status not in (403, 429):
                        retry.error = e
                        continue
                self._error_or_warning(e, fatal=fatal)
                break

            try:
                self._extract_and_report_alerts(data)
            except ExtractorError as e:
                self._error_or_warning(e, fatal=fatal)
                break

            # Sometimes youtube returns a webpage with incomplete ytInitialData
            # See: https://github.com/yt-dlp/yt-dlp/issues/116
            if not traverse_obj(data, 'contents', 'currentVideoEndpoint', 'onResponseReceivedActions'):
                retry.error = ExtractorError('Incomplete yt initial data received')
                data = None
                continue

        return webpage, data

    def _report_playlist_authcheck(self, ytcfg, fatal=True):
        """Use if failed to extract ytcfg (and data) from initial webpage"""
        if not ytcfg and self.is_authenticated:
            msg = 'Playlists that require authentication may not extract correctly without a successful webpage download'
            if 'authcheck' not in self._configuration_arg('skip', ie_key=YoutubeTabIE.ie_key()) and fatal:
                raise ExtractorError(
                    f'{msg}. If you are not downloading private content, or '
                    'your cookies are only for the first account and channel,'
                    ' pass "--extractor-args youtubetab:skip=authcheck" to skip this check',
                    expected=True)
            self.report_warning(msg, only_once=True)

    def _extract_data(self, url, item_id, ytcfg=None, fatal=True, webpage_fatal=False, default_client='web'):
        data = None
        if not self.skip_webpage:
            webpage, data = self._extract_webpage(url, item_id, fatal=webpage_fatal)
            ytcfg = ytcfg or self.extract_ytcfg(item_id, webpage)
            # Reject webpage data if redirected to home page without explicitly requesting
            selected_tab = self._extract_selected_tab(self._extract_tab_renderers(data), fatal=False) or {}
            if (url != 'https://www.youtube.com/feed/recommended'
                    and selected_tab.get('tabIdentifier') == 'FEwhat_to_watch'  # Home page
                    and 'no-youtube-channel-redirect' not in self.get_param('compat_opts', [])):
                msg = 'The channel/playlist does not exist and the URL redirected to youtube.com home page'
                if fatal:
                    raise ExtractorError(msg, expected=True)
                self.report_warning(msg, only_once=True)
        if not data:
            self._report_playlist_authcheck(ytcfg, fatal=fatal)
            data = self._extract_tab_endpoint(url, item_id, ytcfg, fatal=fatal, default_client=default_client)
        return data, ytcfg

    def _extract_tab_endpoint(self, url, item_id, ytcfg=None, fatal=True, default_client='web'):
        headers = self.generate_api_headers(ytcfg=ytcfg, default_client=default_client)
        resolve_response = self._extract_response(
            item_id=item_id, query={'url': url}, check_get_keys='endpoint', headers=headers, ytcfg=ytcfg, fatal=fatal,
            ep='navigation/resolve_url', note='Downloading API parameters API JSON', default_client=default_client)
        endpoints = {'browseEndpoint': 'browse', 'watchEndpoint': 'next'}
        for ep_key, ep in endpoints.items():
            params = try_get(resolve_response, lambda x: x['endpoint'][ep_key], dict)
            if params:
                return self._extract_response(
                    item_id=item_id, query=params, ep=ep, headers=headers,
                    ytcfg=ytcfg, fatal=fatal, default_client=default_client,
                    check_get_keys=('contents', 'currentVideoEndpoint', 'onResponseReceivedActions'))
        err_note = 'Failed to resolve url (does the playlist exist?)'
        if fatal:
            raise ExtractorError(err_note, expected=True)
        self.report_warning(err_note, item_id)

    _SEARCH_PARAMS = None

    def _search_results(self, query, params=NO_DEFAULT, default_client='web'):
        data = {'query': query}
        if params is NO_DEFAULT:
            params = self._SEARCH_PARAMS
        if params:
            data['params'] = params

        content_keys = (
            ('contents', 'twoColumnSearchResultsRenderer', 'primaryContents', 'sectionListRenderer', 'contents'),
            ('onResponseReceivedCommands', 0, 'appendContinuationItemsAction', 'continuationItems'),
            # ytmusic search
            ('contents', 'tabbedSearchResultsRenderer', 'tabs', 0, 'tabRenderer', 'content', 'sectionListRenderer', 'contents'),
            ('continuationContents', ),
        )
        display_id = f'query "{query}"'
        check_get_keys = tuple({keys[0] for keys in content_keys})
        ytcfg = self._download_ytcfg(default_client, display_id) if not self.skip_webpage else {}
        self._report_playlist_authcheck(ytcfg, fatal=False)

        continuation_list = [None]
        search = None
        for page_num in itertools.count(1):
            data.update(continuation_list[0] or {})
            headers = self.generate_api_headers(
                ytcfg=ytcfg, visitor_data=self._extract_visitor_data(search), default_client=default_client)
            search = self._extract_response(
                item_id=f'{display_id} page {page_num}', ep='search', query=data,
                default_client=default_client, check_get_keys=check_get_keys, ytcfg=ytcfg, headers=headers)
            slr_contents = traverse_obj(search, *content_keys)
            yield from self._extract_entries({'contents': list(variadic(slr_contents))}, continuation_list)
            if not continuation_list[0]:
                break


class YoutubeTabIE(YoutubeTabBaseInfoExtractor):
    IE_DESC = 'YouTube Tabs'
    _VALID_URL = r'''(?x:
        https?://
            (?!consent\.)(?:\w+\.)?
            (?:
                youtube(?:kids)?\.com|
                {invidious}
            )/
            (?:
                (?P<channel_type>channel|c|user|browse)/|
                (?P<not_channel>
                    feed/|hashtag/|
                    (?:playlist|watch)\?.*?\blist=
                )|
                (?!(?:{reserved_names})\b)  # Direct URLs
            )
            (?P<id>[^/?\#&]+)
    )'''.format(
        reserved_names=YoutubeBaseInfoExtractor._RESERVED_NAMES,
        invidious='|'.join(YoutubeBaseInfoExtractor._INVIDIOUS_SITES),
    )
    IE_NAME = 'youtube:tab'

    _TESTS = [{
        'note': 'playlists, multipage',
        'url': 'https://www.youtube.com/c/ИгорьКлейнер/playlists?view=1&flow=grid',
        'playlist_mincount': 94,
        'info_dict': {
            'id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'title': 'Igor Kleiner  - Playlists',
            'description': r're:(?s)Добро пожаловать на мой канал! Здесь вы найдете видео .{504}/a1/50b/10a$',
            'uploader': 'Igor Kleiner ',
            'uploader_id': '@IgorDataScience',
            'uploader_url': 'https://www.youtube.com/@IgorDataScience',
            'channel': 'Igor Kleiner ',
            'channel_id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'tags': 'count:23',
            'channel_url': 'https://www.youtube.com/channel/UCqj7Cz7revf5maW9g5pgNcg',
            'channel_follower_count': int,
        },
    }, {
        'note': 'playlists, multipage, different order',
        'url': 'https://www.youtube.com/user/igorkle1/playlists?view=1&sort=dd',
        'playlist_mincount': 94,
        'info_dict': {
            'id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'title': 'Igor Kleiner  - Playlists',
            'description': r're:(?s)Добро пожаловать на мой канал! Здесь вы найдете видео .{504}/a1/50b/10a$',
            'uploader': 'Igor Kleiner ',
            'uploader_id': '@IgorDataScience',
            'uploader_url': 'https://www.youtube.com/@IgorDataScience',
            'tags': 'count:23',
            'channel_id': 'UCqj7Cz7revf5maW9g5pgNcg',
            'channel': 'Igor Kleiner ',
            'channel_url': 'https://www.youtube.com/channel/UCqj7Cz7revf5maW9g5pgNcg',
            'channel_follower_count': int,
        },
    }, {
        # TODO: fix channel_is_verified extraction
        'note': 'playlists, series',
        'url': 'https://www.youtube.com/c/3blue1brown/playlists?view=50&sort=dd&shelf_id=3',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'UCYO_jab_esuFRV4b17AJtAw',
            'title': '3Blue1Brown - Playlists',
            'description': 'md5:602e3789e6a0cb7d9d352186b720e395',
            'channel_url': 'https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw',
            'channel': '3Blue1Brown',
            'channel_id': 'UCYO_jab_esuFRV4b17AJtAw',
            'uploader_id': '@3blue1brown',
            'uploader_url': 'https://www.youtube.com/@3blue1brown',
            'uploader': '3Blue1Brown',
            'tags': ['Mathematics'],
            'channel_follower_count': int,
            'channel_is_verified': True,
        },
    }, {
        'note': 'playlists, singlepage',
        'url': 'https://www.youtube.com/user/ThirstForScience/playlists',
        'playlist_mincount': 4,
        'info_dict': {
            'id': 'UCAEtajcuhQ6an9WEzY9LEMQ',
            'title': 'ThirstForScience - Playlists',
            'description': 'md5:609399d937ea957b0f53cbffb747a14c',
            'uploader': 'ThirstForScience',
            'uploader_url': 'https://www.youtube.com/@ThirstForScience',
            'uploader_id': '@ThirstForScience',
            'channel_id': 'UCAEtajcuhQ6an9WEzY9LEMQ',
            'channel_url': 'https://www.youtube.com/channel/UCAEtajcuhQ6an9WEzY9LEMQ',
            'tags': 'count:12',
            'channel': 'ThirstForScience',
            'channel_follower_count': int,
        },
    }, {
        'url': 'https://www.youtube.com/c/ChristophLaimer/playlists',
        'only_matching': True,
    }, {
        # TODO: fix availability and view_count extraction
        'note': 'basic, single video playlist',
        'url': 'https://www.youtube.com/playlist?list=PLt5yu3-wZAlSLRHmI1qNm0wjyVNWw1pCU',
        'info_dict': {
            'id': 'PLt5yu3-wZAlSLRHmI1qNm0wjyVNWw1pCU',
            'title': 'single video playlist',
            'description': '',
            'tags': [],
            'view_count': int,
            'modified_date': '20250417',
            'channel': 'cole-dlp-test-acc',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'availability': 'public',
            'uploader': 'cole-dlp-test-acc',
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
        },
        'playlist_count': 1,
    }, {
        'note': 'empty playlist',
        'url': 'https://www.youtube.com/playlist?list=PL4lCao7KL_QFodcLWhDpGCYnngnHtQ-Xf',
        'info_dict': {
            'id': 'PL4lCao7KL_QFodcLWhDpGCYnngnHtQ-Xf',
            'title': 'youtube-dl empty playlist',
            'tags': [],
            'channel': 'Sergey M.',
            'description': '',
            'modified_date': '20230921',
            'channel_id': 'UCmlqkdCBesrv2Lak1mF_MxA',
            'channel_url': 'https://www.youtube.com/channel/UCmlqkdCBesrv2Lak1mF_MxA',
            'availability': 'unlisted',
            'uploader_url': 'https://www.youtube.com/@sergeym.6173',
            'uploader_id': '@sergeym.6173',
            'uploader': 'Sergey M.',
        },
        'playlist_count': 0,
    }, {
        'note': 'Home tab',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/featured',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Home',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': '@lexwill718',
            'channel': 'lex will',
            'tags': ['bible', 'history', 'prophesy'],
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_follower_count': int,
        },
        'playlist_mincount': 2,
    }, {
        'note': 'Videos tab',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/videos',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Videos',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': '@lexwill718',
            'tags': ['bible', 'history', 'prophesy'],
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'channel': 'lex will',
            'channel_follower_count': int,
        },
        'playlist_mincount': 975,
    }, {
        'note': 'Videos tab, sorted by popular',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/videos?view=0&sort=p&flow=grid',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Videos',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': '@lexwill718',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'channel': 'lex will',
            'tags': ['bible', 'history', 'prophesy'],
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_follower_count': int,
        },
        'playlist_mincount': 199,
    }, {
        'note': 'Playlists tab',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/playlists',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Playlists',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'uploader': 'lex will',
            'uploader_id': '@lexwill718',
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'channel': 'lex will',
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'tags': ['bible', 'history', 'prophesy'],
            'channel_follower_count': int,
        },
        'playlist_mincount': 17,
    }, {
        'note': 'Posts tab',
        'url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w/community',
        'info_dict': {
            'id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'title': 'lex will - Posts',
            'description': 'md5:2163c5d0ff54ed5f598d6a7e6211e488',
            'channel': 'lex will',
            'channel_url': 'https://www.youtube.com/channel/UCKfVa3S1e4PHvxWcwyMMg8w',
            'channel_id': 'UCKfVa3S1e4PHvxWcwyMMg8w',
            'tags': ['bible', 'history', 'prophesy'],
            'channel_follower_count': int,
            'uploader_url': 'https://www.youtube.com/@lexwill718',
            'uploader_id': '@lexwill718',
            'uploader': 'lex will',
        },
        'playlist_mincount': 18,
        'skip': 'This Community isn\'t available',
    }, {
        # TODO: fix channel_is_verified extraction
        'note': 'Search tab',
        'url': 'https://www.youtube.com/c/3blue1brown/search?query=linear%20algebra',
        'playlist_mincount': 40,
        'info_dict': {
            'id': 'UCYO_jab_esuFRV4b17AJtAw',
            'title': '3Blue1Brown - Search - linear algebra',
            'description': 'md5:602e3789e6a0cb7d9d352186b720e395',
            'channel_url': 'https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw',
            'tags': ['Mathematics'],
            'channel': '3Blue1Brown',
            'channel_id': 'UCYO_jab_esuFRV4b17AJtAw',
            'channel_follower_count': int,
            'uploader_url': 'https://www.youtube.com/@3blue1brown',
            'uploader_id': '@3blue1brown',
            'uploader': '3Blue1Brown',
            'channel_is_verified': True,
        },
    }, {
        'url': 'https://invidio.us/channel/UCmlqkdCBesrv2Lak1mF_MxA',
        'only_matching': True,
    }, {
        'url': 'https://www.youtubekids.com/channel/UCmlqkdCBesrv2Lak1mF_MxA',
        'only_matching': True,
    }, {
        'url': 'https://music.youtube.com/channel/UCmlqkdCBesrv2Lak1mF_MxA',
        'only_matching': True,
    }, {
        # TODO: fix availability extraction
        'note': 'Playlist with deleted videos (#651). As a bonus, the video #51 is also twice in this list.',
        'url': 'https://www.youtube.com/playlist?list=PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC',
        'info_dict': {
            'title': '29C3: Not my department',
            'id': 'PLwP_SiAcdui0KVebT0mU9Apz359a4ubsC',
            'description': 'md5:a14dc1a8ef8307a9807fe136a0660268',
            'tags': [],
            'view_count': int,
            'modified_date': '20150605',
            'channel_id': 'UCEPzS1rYsrkqzSLNp76nrcg',
            'channel_url': 'https://www.youtube.com/channel/UCEPzS1rYsrkqzSLNp76nrcg',
            'channel': 'Christiaan008',
            'availability': 'public',
            'uploader_id': '@ChRiStIaAn008',
            'uploader': 'Christiaan008',
            'uploader_url': 'https://www.youtube.com/@ChRiStIaAn008',
        },
        'playlist_count': 96,
    }, {
        'note': 'Large playlist',
        'url': 'https://www.youtube.com/playlist?list=UUBABnxM4Ar9ten8Mdjj1j0Q',
        'info_dict': {
            'title': 'Uploads from Cauchemar',
            'id': 'UUBABnxM4Ar9ten8Mdjj1j0Q',
            'channel_url': 'https://www.youtube.com/channel/UCBABnxM4Ar9ten8Mdjj1j0Q',
            'tags': [],
            'modified_date': r're:\d{8}',
            'channel': 'Cauchemar',
            'view_count': int,
            'description': '',
            'channel_id': 'UCBABnxM4Ar9ten8Mdjj1j0Q',
            'availability': 'public',
            'uploader_id': '@Cauchemar89',
            'uploader': 'Cauchemar',
            'uploader_url': 'https://www.youtube.com/@Cauchemar89',
        },
        'playlist_mincount': 1123,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'note': 'even larger playlist, 8832 videos',
        'url': 'http://www.youtube.com/user/NASAgovVideo/videos',
        'only_matching': True,
    }, {
        'note': 'Buggy playlist: the webpage has a "Load more" button but it doesn\'t have more videos',
        'url': 'https://www.youtube.com/playlist?list=UUXw-G3eDE9trcvY2sBMM_aA',
        'info_dict': {
            'title': 'Uploads from Interstellar Movie',
            'id': 'UUXw-G3eDE9trcvY2sBMM_aA',
            'tags': [],
            'view_count': int,
            'channel_id': 'UCXw-G3eDE9trcvY2sBMM_aA',
            'channel_url': 'https://www.youtube.com/channel/UCXw-G3eDE9trcvY2sBMM_aA',
            'channel': 'Interstellar Movie',
            'description': '',
            'modified_date': r're:\d{8}',
            'availability': 'public',
            'uploader_id': '@InterstellarMovie',
            'uploader': 'Interstellar Movie',
            'uploader_url': 'https://www.youtube.com/@InterstellarMovie',
        },
        'playlist_mincount': 21,
    }, {
        # TODO: fix availability extraction
        'note': 'Playlist with "show unavailable videos" button',
        'url': 'https://www.youtube.com/playlist?list=PLYwq8WOe86_xGmR7FrcJq8Sb7VW8K3Tt2',
        'info_dict': {
            'title': 'The Memes Of 2010s.....',
            'id': 'PLYwq8WOe86_xGmR7FrcJq8Sb7VW8K3Tt2',
            'view_count': int,
            'channel': "I'm Not JiNxEd",
            'tags': [],
            'description': 'md5:44dc3b315ba69394feaafa2f40e7b2a1',
            'channel_url': 'https://www.youtube.com/channel/UC5H5H85D1QE5-fuWWQ1hdNg',
            'channel_id': 'UC5H5H85D1QE5-fuWWQ1hdNg',
            'modified_date': r're:\d{8}',
            'availability': 'public',
            'uploader_url': 'https://www.youtube.com/@imnotjinxed1998',
            'uploader_id': '@imnotjinxed1998',
            'uploader': "I'm Not JiNxEd",
        },
        'playlist_mincount': 150,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'note': 'Playlist with unavailable videos in page 7',
        'url': 'https://www.youtube.com/playlist?list=UU8l9frL61Yl5KFOl87nIm2w',
        'info_dict': {
            'title': 'Uploads from BlankTV',
            'id': 'UU8l9frL61Yl5KFOl87nIm2w',
            'channel': 'BlankTV',
            'channel_url': 'https://www.youtube.com/channel/UC8l9frL61Yl5KFOl87nIm2w',
            'channel_id': 'UC8l9frL61Yl5KFOl87nIm2w',
            'view_count': int,
            'tags': [],
            'modified_date': r're:\d{8}',
            'description': '',
            'availability': 'public',
            'uploader_id': '@blanktv',
            'uploader': 'BlankTV',
            'uploader_url': 'https://www.youtube.com/@blanktv',
        },
        'playlist_mincount': 1000,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        # TODO: fix availability extraction
        'note': 'https://github.com/ytdl-org/youtube-dl/issues/21844',
        'url': 'https://www.youtube.com/playlist?list=PLzH6n4zXuckpfMu_4Ff8E7Z1behQks5ba',
        'info_dict': {
            'title': 'Data Analysis with Dr Mike Pound',
            'id': 'PLzH6n4zXuckpfMu_4Ff8E7Z1behQks5ba',
            'description': 'md5:7f567c574d13d3f8c0954d9ffee4e487',
            'tags': [],
            'view_count': int,
            'channel_id': 'UC9-y-6csu5WGm29I7JiwpnA',
            'channel_url': 'https://www.youtube.com/channel/UC9-y-6csu5WGm29I7JiwpnA',
            'channel': 'Computerphile',
            'availability': 'public',
            'modified_date': '20190712',
            'uploader_id': '@Computerphile',
            'uploader': 'Computerphile',
            'uploader_url': 'https://www.youtube.com/@Computerphile',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://invidio.us/playlist?list=PL4lCao7KL_QFVb7Iudeipvc2BCavECqzc',
        'only_matching': True,
    }, {
        'note': 'Playlist URL that does not actually serve a playlist',
        'url': 'https://www.youtube.com/watch?v=FqZTN594JQw&list=PLMYEtVRpaqY00V9W81Cwmzp6N6vZqfUKD4',
        'info_dict': {
            'id': 'FqZTN594JQw',
            'ext': 'webm',
            'title': "Smiley's People 01 detective, Adventure Series, Action",
            'upload_date': '20150526',
            'license': 'Standard YouTube License',
            'description': 'md5:507cdcb5a49ac0da37a920ece610be80',
            'categories': ['People & Blogs'],
            'tags': list,
            'view_count': int,
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'This video is not available.',
        'add_ie': [YoutubeIE.ie_key()],
    }, {
        'url': 'https://www.youtubekids.com/watch?v=Agk7R8I8o5U&list=PUZ6jURNr1WQZCNHF0ao-c0g',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/watch?v=MuAGGZNfUkU&list=RDMM',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/channel/UCoMdktPbSTixAyNGwb-UYkQ/live',
        'info_dict': {
            'id': 'VFGoUmo74wE',  # This will keep changing
            'ext': 'mp4',
            'title': str,
            'upload_date': r're:\d{8}',
            'description': str,
            'categories': ['News & Politics'],
            'tags': list,
            'like_count': int,
            'release_timestamp': int,
            'channel': 'Sky News',
            'channel_id': 'UCoMdktPbSTixAyNGwb-UYkQ',
            'age_limit': 0,
            'view_count': int,
            'thumbnail': r're:https?://i\.ytimg\.com/vi/[^/]+/maxresdefault(?:_live)?\.jpg',
            'playable_in_embed': True,
            'release_date': r're:\d+',
            'availability': 'public',
            'live_status': 'is_live',
            'channel_url': 'https://www.youtube.com/channel/UCoMdktPbSTixAyNGwb-UYkQ',
            'channel_follower_count': int,
            'concurrent_view_count': int,
            'uploader_url': 'https://www.youtube.com/@SkyNews',
            'uploader_id': '@SkyNews',
            'uploader': 'Sky News',
            'channel_is_verified': True,
            'media_type': 'livestream',
            'timestamp': int,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Ignoring subtitle tracks found in '],
    }, {
        'url': 'https://www.youtube.com/user/TheYoungTurks/live',
        'info_dict': {
            'id': 'a48o2S1cPoo',
            'ext': 'mp4',
            'title': 'The Young Turks - Live Main Show',
            'upload_date': '20150715',
            'license': 'Standard YouTube License',
            'description': 'md5:438179573adcdff3c97ebb1ee632b891',
            'categories': ['News & Politics'],
            'tags': ['Cenk Uygur (TV Program Creator)', 'The Young Turks (Award-Winning Work)', 'Talk Show (TV Genre)'],
            'like_count': int,
        },
        'params': {
            'skip_download': True,
        },
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/channel/UC1yBKRuGpC1tSM73A0ZjYjQ/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/c/CommanderVideoHq/live',
        'only_matching': True,
    }, {
        'note': 'A channel that is not live. Should raise error',
        'url': 'https://www.youtube.com/user/numberphile/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/trending',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/library',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/history',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/subscriptions',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/feed/watch_later',
        'only_matching': True,
    }, {
        'note': 'Recommended - redirects to home page.',
        'url': 'https://www.youtube.com/feed/recommended',
        'only_matching': True,
    }, {
        'note': 'inline playlist with not always working continuations',
        'url': 'https://www.youtube.com/watch?v=UC6u0Tct-Fo&list=PL36D642111D65BE7C',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/course',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/zsecurity',
        'only_matching': True,
    }, {
        'url': 'http://www.youtube.com/NASAgovVideo/videos',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/TheYoungTurks/live',
        'only_matching': True,
    }, {
        'url': 'https://www.youtube.com/hashtag/cctv9',
        'info_dict': {
            'id': 'cctv9',
            'title': 'cctv9 - All',
            'tags': [],
        },
        'playlist_mincount': 300,  # not consistent but should be over 300
    }, {
        'url': 'https://www.youtube.com/watch?list=PLW4dVinRY435CBE_JD3t-0SRXKfnZHS1P&feature=youtu.be&v=M9cJMXmQ_ZU',
        'only_matching': True,
    }, {
        'note': 'Requires Premium: should request additional YTM-info webpage (and have format 141) for videos in playlist',
        'url': 'https://music.youtube.com/playlist?list=PLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
        'only_matching': True,
    }, {
        'note': '/browse/ should redirect to /channel/',
        'url': 'https://music.youtube.com/browse/UC1a8OFewdjuLq6KlF8M_8Ng',
        'only_matching': True,
    }, {
        # TODO: fix availability extraction
        'note': 'VLPL, should redirect to playlist?list=PL...',
        'url': 'https://music.youtube.com/browse/VLPLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
        'info_dict': {
            'id': 'PLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
            'description': 'Providing you with copyright free / safe music for gaming, live streaming, studying and more!',
            'title': 'NCS : All Releases 💿',
            'channel_url': 'https://www.youtube.com/channel/UC_aEa8K-EOJ3D6gOs7HcyNg',
            'modified_date': r're:\d{8}',
            'view_count': int,
            'channel_id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
            'tags': [],
            'channel': 'NoCopyrightSounds',
            'availability': 'public',
            'uploader_url': 'https://www.youtube.com/@NoCopyrightSounds',
            'uploader': 'NoCopyrightSounds',
            'uploader_id': '@NoCopyrightSounds',
        },
        'playlist_mincount': 166,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden', 'YouTube Music is not directly supported'],
    }, {
        # TODO: fix 'unviewable' issue with this playlist when reloading with unavailable videos
        'note': 'Topic, should redirect to playlist?list=UU...',
        'url': 'https://music.youtube.com/browse/UC9ALqqC4aIeG5iDs7i90Bfw',
        'info_dict': {
            'id': 'UU9ALqqC4aIeG5iDs7i90Bfw',
            'title': 'Uploads from Royalty Free Music - Topic',
            'tags': [],
            'channel_id': 'UC9ALqqC4aIeG5iDs7i90Bfw',
            'channel': 'Royalty Free Music - Topic',
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UC9ALqqC4aIeG5iDs7i90Bfw',
            'modified_date': r're:\d{8}',
            'description': '',
            'availability': 'public',
            'uploader': 'Royalty Free Music - Topic',
        },
        'playlist_mincount': 101,
        'expected_warnings': ['YouTube Music is not directly supported', r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        # Destination channel with only a hidden self tab (tab id is UCtFRv9O2AHqOZjjynzrv-xg)
        # Treat as a general feed
        # TODO: fix extraction
        'url': 'https://www.youtube.com/channel/UCtFRv9O2AHqOZjjynzrv-xg',
        'info_dict': {
            'id': 'UCtFRv9O2AHqOZjjynzrv-xg',
            'title': 'UCtFRv9O2AHqOZjjynzrv-xg',
            'tags': [],
        },
        'playlist_mincount': 9,
    }, {
        'note': 'Youtube music Album',
        'url': 'https://music.youtube.com/browse/MPREb_gTAcphH99wE',
        'info_dict': {
            'id': 'OLAK5uy_l1m0thk3g31NmIIz_vMIbWtyv7eZixlH0',
            'title': 'Album - Royalty Free Music Library V2 (50 Songs)',
            'tags': [],
            'view_count': int,
            'description': '',
            'availability': 'unlisted',
            'modified_date': r're:\d{8}',
        },
        'playlist_count': 50,
        'expected_warnings': ['YouTube Music is not directly supported'],
    }, {
        'note': 'unlisted single video playlist',
        'url': 'https://www.youtube.com/playlist?list=PLt5yu3-wZAlQLfIN0MMgp0wVV6MP3bM4_',
        'info_dict': {
            'id': 'PLt5yu3-wZAlQLfIN0MMgp0wVV6MP3bM4_',
            'title': 'unlisted playlist',
            'availability': 'unlisted',
            'tags': [],
            'modified_date': '20250417',
            'channel': 'cole-dlp-test-acc',
            'view_count': int,
            'description': '',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
            'uploader': 'cole-dlp-test-acc',
        },
        'playlist': [{
            'info_dict': {
                'title': 'Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film',
                'id': 'aqz-KE-bpKQ',
                '_type': 'url',
                'ie_key': 'Youtube',
                'duration': 635,
                'channel_id': 'UCSMOQeBJ2RAnuFungnQOxLg',
                'channel_url': 'https://www.youtube.com/channel/UCSMOQeBJ2RAnuFungnQOxLg',
                'view_count': int,
                'url': 'https://www.youtube.com/watch?v=aqz-KE-bpKQ',
                'channel': 'Blender',
                'uploader_id': '@BlenderOfficial',
                'uploader_url': 'https://www.youtube.com/@BlenderOfficial',
                'uploader': 'Blender',
            },
        }],
        'playlist_count': 1,
        'params': {'extract_flat': True},
    }, {
        # By default, recommended is always empty.
        'note': 'API Fallback: Recommended - redirects to home page. Requires visitorData',
        'url': 'https://www.youtube.com/feed/recommended',
        'info_dict': {
            'id': 'recommended',
            'title': 'recommended',
            'tags': [],
        },
        'playlist_count': 0,
        'params': {
            'skip_download': True,
            'extractor_args': {'youtubetab': {'skip': ['webpage']}},
        },
    }, {
        'note': 'API Fallback: /videos tab, sorted by oldest first',
        'url': 'https://www.youtube.com/user/theCodyReeder/videos?view=0&sort=da&flow=grid',
        'info_dict': {
            'id': 'UCu6mSoMNzHQiBIOCkHUa2Aw',
            'title': 'Cody\'sLab - Videos',
            'description': 'md5:d083b7c2f0c67ee7a6c74c3e9b4243fa',
            'channel': 'Cody\'sLab',
            'channel_id': 'UCu6mSoMNzHQiBIOCkHUa2Aw',
            'tags': [],
            'channel_url': 'https://www.youtube.com/channel/UCu6mSoMNzHQiBIOCkHUa2Aw',
            'channel_follower_count': int,
        },
        'playlist_mincount': 650,
        'params': {
            'skip_download': True,
            'extractor_args': {'youtubetab': {'skip': ['webpage']}},
        },
        'skip': 'Query for sorting no longer works',
    }, {
        # TODO: fix 'unviewable' issue with this playlist when reloading with unavailable videos
        'note': 'API Fallback: Topic, should redirect to playlist?list=UU...',
        'url': 'https://music.youtube.com/browse/UC9ALqqC4aIeG5iDs7i90Bfw',
        'info_dict': {
            'id': 'UU9ALqqC4aIeG5iDs7i90Bfw',
            'title': 'Uploads from Royalty Free Music - Topic',
            'modified_date': r're:\d{8}',
            'channel_id': 'UC9ALqqC4aIeG5iDs7i90Bfw',
            'description': '',
            'channel_url': 'https://www.youtube.com/channel/UC9ALqqC4aIeG5iDs7i90Bfw',
            'tags': [],
            'channel': 'Royalty Free Music - Topic',
            'view_count': int,
            'availability': 'public',
            'uploader': 'Royalty Free Music - Topic',
        },
        'playlist_mincount': 101,
        'params': {
            'skip_download': True,
            'extractor_args': {'youtubetab': {'skip': ['webpage']}},
        },
        'expected_warnings': ['YouTube Music is not directly supported', r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'note': 'non-standard redirect to regional channel',
        'url': 'https://www.youtube.com/channel/UCwVVpHQ2Cs9iGJfpdFngePQ',
        'only_matching': True,
    }, {
        'note': 'collaborative playlist (uploader name in the form "by <uploader> and x other(s)")',
        'url': 'https://www.youtube.com/playlist?list=PLx-_-Kk4c89oOHEDQAojOXzEzemXxoqx6',
        'info_dict': {
            'id': 'PLx-_-Kk4c89oOHEDQAojOXzEzemXxoqx6',
            'modified_date': '20250115',
            'channel_url': 'https://www.youtube.com/channel/UCKcqXmCcyqnhgpA5P0oHH_Q',
            'tags': [],
            'availability': 'unlisted',
            'channel_id': 'UCKcqXmCcyqnhgpA5P0oHH_Q',
            'channel': 'pukkandan',
            'description': 'Test for collaborative playlist',
            'title': 'yt-dlp test - collaborative playlist',
            'view_count': int,
            'uploader_url': 'https://www.youtube.com/@pukkandan',
            'uploader_id': '@pukkandan',
            'uploader': 'pukkandan',
        },
        'playlist_mincount': 2,
        'skip': 'https://github.com/yt-dlp/yt-dlp/issues/13690',
    }, {
        'note': 'translated tab name',
        'url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA/playlists',
        'info_dict': {
            'id': 'UCiu-3thuViMebBjw_5nWYrA',
            'tags': [],
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'description': 'test description',
            'title': 'cole-dlp-test-acc - 再生リスト',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel': 'cole-dlp-test-acc',
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
            'uploader': 'cole-dlp-test-acc',
        },
        'playlist_mincount': 1,
        'params': {'extractor_args': {'youtube': {'lang': ['ja']}}},
        'expected_warnings': ['Preferring "ja"'],
    }, {
        # XXX: this should really check flat playlist entries, but the test suite doesn't support that
        # TODO: fix availability extraction
        'note': 'preferred lang set with playlist with translated video titles',
        'url': 'https://www.youtube.com/playlist?list=PLt5yu3-wZAlQAaPZ5Z-rJoTdbT-45Q7c0',
        'info_dict': {
            'id': 'PLt5yu3-wZAlQAaPZ5Z-rJoTdbT-45Q7c0',
            'tags': [],
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'channel': 'cole-dlp-test-acc',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'description': 'test',
            'title': 'dlp test playlist',
            'availability': 'public',
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
            'uploader': 'cole-dlp-test-acc',
        },
        'playlist_mincount': 1,
        'params': {'extractor_args': {'youtube': {'lang': ['ja']}}},
        'expected_warnings': ['Preferring "ja"'],
    }, {
        # shorts audio pivot for 2GtVksBMYFM.
        'url': 'https://www.youtube.com/feed/sfv_audio_pivot?bp=8gUrCikSJwoLMkd0VmtzQk1ZRk0SCzJHdFZrc0JNWUZNGgsyR3RWa3NCTVlGTQ==',
        # TODO: fix extraction
        'info_dict': {
            'id': 'sfv_audio_pivot',
            'title': 'sfv_audio_pivot',
            'tags': [],
        },
        'playlist_mincount': 50,

    }, {
        # Channel with a real live tab (not to be mistaken with streams tab)
        # Do not treat like it should redirect to live stream
        'url': 'https://www.youtube.com/channel/UCEH7P7kyJIkS_gJf93VYbmg/live',
        'info_dict': {
            'id': 'UCEH7P7kyJIkS_gJf93VYbmg',
            'title': 'UCEH7P7kyJIkS_gJf93VYbmg - Live',
            'tags': [],
        },
        'playlist_mincount': 20,
    }, {
        # Tab name is not the same as tab id
        'url': 'https://www.youtube.com/channel/UCQvWX73GQygcwXOTSf_VDVg/letsplay',
        'info_dict': {
            'id': 'UCQvWX73GQygcwXOTSf_VDVg',
            'title': 'UCQvWX73GQygcwXOTSf_VDVg - Let\'s play',
            'tags': [],
        },
        'playlist_mincount': 8,
    }, {
        # Home tab id is literally home. Not to get mistaken with featured
        'url': 'https://www.youtube.com/channel/UCQvWX73GQygcwXOTSf_VDVg/home',
        'info_dict': {
            'id': 'UCQvWX73GQygcwXOTSf_VDVg',
            'title': 'UCQvWX73GQygcwXOTSf_VDVg - Home',
            'tags': [],
        },
        'playlist_mincount': 8,
    }, {
        # Should get three playlists for videos, shorts and streams tabs
        # TODO: fix channel_is_verified extraction
        'url': 'https://www.youtube.com/channel/UCK9V2B22uJYu3N7eR_BT9QA',
        'info_dict': {
            'id': 'UCK9V2B22uJYu3N7eR_BT9QA',
            'title': 'Polka Ch. 尾丸ポルカ',
            'channel_follower_count': int,
            'channel_id': 'UCK9V2B22uJYu3N7eR_BT9QA',
            'channel_url': 'https://www.youtube.com/channel/UCK9V2B22uJYu3N7eR_BT9QA',
            'description': 'md5:01e53f350ab8ad6fcf7c4fedb3c1b99f',
            'channel': 'Polka Ch. 尾丸ポルカ',
            'tags': 'count:35',
            'uploader_url': 'https://www.youtube.com/@OmaruPolka',
            'uploader': 'Polka Ch. 尾丸ポルカ',
            'uploader_id': '@OmaruPolka',
            'channel_is_verified': True,
        },
        'playlist_count': 3,
    }, {
        # Shorts tab with channel with handle
        # TODO: fix channel_is_verified extraction
        'url': 'https://www.youtube.com/@NotJustBikes/shorts',
        'info_dict': {
            'id': 'UC0intLFzLaudFG-xAvUEO-A',
            'title': 'Not Just Bikes - Shorts',
            'tags': 'count:10',
            'channel_url': 'https://www.youtube.com/channel/UC0intLFzLaudFG-xAvUEO-A',
            'description': 'md5:295758591d0d43d8594277be54584da7',
            'channel_follower_count': int,
            'channel_id': 'UC0intLFzLaudFG-xAvUEO-A',
            'channel': 'Not Just Bikes',
            'uploader_url': 'https://www.youtube.com/@NotJustBikes',
            'uploader': 'Not Just Bikes',
            'uploader_id': '@NotJustBikes',
            'channel_is_verified': True,
        },
        'playlist_mincount': 10,
    }, {
        # Streams tab
        'url': 'https://www.youtube.com/channel/UC3eYAvjCVwNHgkaGbXX3sig/streams',
        'info_dict': {
            'id': 'UC3eYAvjCVwNHgkaGbXX3sig',
            'title': '中村悠一 - Live',
            'tags': 'count:7',
            'channel_id': 'UC3eYAvjCVwNHgkaGbXX3sig',
            'channel_url': 'https://www.youtube.com/channel/UC3eYAvjCVwNHgkaGbXX3sig',
            'channel': '中村悠一',
            'channel_follower_count': int,
            'description': 'md5:76b312b48a26c3b0e4d90e2dfc1b417d',
            'uploader_url': 'https://www.youtube.com/@Yuichi-Nakamura',
            'uploader_id': '@Yuichi-Nakamura',
            'uploader': '中村悠一',
        },
        'playlist_mincount': 60,
    }, {
        # Channel with no uploads and hence no videos, streams, shorts tabs or uploads playlist. This should fail.
        # See test_youtube_lists
        'url': 'https://www.youtube.com/channel/UC2yXPzFejc422buOIzn_0CA',
        'only_matching': True,
    }, {
        # No uploads and no UCID given. Should fail with no uploads error
        # See test_youtube_lists
        'url': 'https://www.youtube.com/news',
        'only_matching': True,
    }, {
        # No videos tab but has a shorts tab
        # TODO: fix metadata extraction
        'url': 'https://www.youtube.com/c/TKFShorts',
        'info_dict': {
            'id': 'UCgJ5_1F6yJhYLnyMszUdmUg',
            'title': 'Shorts Break - Shorts',
            'tags': 'count:48',
            'channel_id': 'UCgJ5_1F6yJhYLnyMszUdmUg',
            'channel': 'Shorts Break',
            'description': 'md5:6de33c5e7ba686e5f3efd4e19c7ef499',
            'channel_follower_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCgJ5_1F6yJhYLnyMszUdmUg',
            'uploader_url': 'https://www.youtube.com/@ShortsBreak_Official',
            'uploader': 'Shorts Break',
            'uploader_id': '@ShortsBreak_Official',
        },
        'playlist_mincount': 30,
    }, {
        # Trending Now Tab. tab id is empty
        'url': 'https://www.youtube.com/feed/trending',
        'info_dict': {
            'id': 'trending',
            'title': 'trending - Now',
            'tags': [],
        },
        'playlist_mincount': 30,
        'skip': 'The channel/playlist does not exist and the URL redirected to youtube.com home page',
    }, {
        # Trending Gaming Tab. tab id is empty
        'url': 'https://www.youtube.com/feed/trending?bp=4gIcGhpnYW1pbmdfY29ycHVzX21vc3RfcG9wdWxhcg%3D%3D',
        'info_dict': {
            'id': 'trending',
            'title': 'trending',
            'tags': [],
        },
        'playlist_mincount': 30,
    }, {
        # Shorts url result in shorts tab
        'url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA/shorts',
        'info_dict': {
            'id': 'UCiu-3thuViMebBjw_5nWYrA',
            'title': 'cole-dlp-test-acc - Shorts',
            'channel': 'cole-dlp-test-acc',
            'description': 'test description',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'tags': [],
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
            'uploader': 'cole-dlp-test-acc',
        },
        'playlist': [{
            'info_dict': {
                # Channel data is not currently available for short renderers (as of 2023-03-01)
                '_type': 'url',
                'ie_key': 'Youtube',
                'url': 'https://www.youtube.com/shorts/sSM9J5YH_60',
                'id': 'sSM9J5YH_60',
                'title': 'SHORT short',
                'view_count': int,
                'thumbnails': list,
            },
        }],
        'params': {'extract_flat': True},
    }, {
        # Live video status should be extracted
        'url': 'https://www.youtube.com/channel/UCQvWX73GQygcwXOTSf_VDVg/live',
        'info_dict': {
            'id': 'UCQvWX73GQygcwXOTSf_VDVg',
            'title': 'UCQvWX73GQygcwXOTSf_VDVg - Live',  # TODO: should be Minecraft - Live or Minecraft - Topic - Live
            'tags': [],
        },
        'playlist': [{
            'info_dict': {
                '_type': 'url',
                'ie_key': 'Youtube',
                'url': 'startswith:https://www.youtube.com/watch?v=',
                'id': str,
                'title': str,
                'live_status': 'is_live',
                'channel_id': str,
                'channel_url': str,
                'concurrent_view_count': int,
                'channel': str,
                'uploader': str,
                'uploader_url': str,
                'uploader_id': str,
                'channel_is_verified': bool,  # this will keep changing
            },
        }],
        'params': {'extract_flat': True, 'playlist_items': '1'},
        'playlist_mincount': 1,
    }, {
        # Channel renderer metadata. Contains number of videos on the channel
        # TODO: channels tab removed, change this test to use another page with channel renderer
        'url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA/channels',
        'info_dict': {
            'id': 'UCiu-3thuViMebBjw_5nWYrA',
            'title': 'cole-dlp-test-acc - Channels',
            'channel': 'cole-dlp-test-acc',
            'description': 'test description',
            'channel_id': 'UCiu-3thuViMebBjw_5nWYrA',
            'channel_url': 'https://www.youtube.com/channel/UCiu-3thuViMebBjw_5nWYrA',
            'tags': [],
            'uploader_url': 'https://www.youtube.com/@coletdjnz',
            'uploader_id': '@coletdjnz',
            'uploader': 'cole-dlp-test-acc',
        },
        'playlist': [{
            'info_dict': {
                '_type': 'url',
                'ie_key': 'YoutubeTab',
                'url': 'https://www.youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'id': 'UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'channel_id': 'UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'title': 'PewDiePie',
                'channel': 'PewDiePie',
                'channel_url': 'https://www.youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'thumbnails': list,
                'channel_follower_count': int,
                'playlist_count': int,
                'uploader': 'PewDiePie',
                'uploader_url': 'https://www.youtube.com/@PewDiePie',
                'uploader_id': '@PewDiePie',
                'channel_is_verified': True,
            },
        }],
        'params': {'extract_flat': True},
        'skip': 'channels tab removed',
    }, {
        # TODO: fix channel_is_verified extraction
        'url': 'https://www.youtube.com/@3blue1brown/about',
        'info_dict': {
            'id': '@3blue1brown',
            'tags': ['Mathematics'],
            'title': '3Blue1Brown',
            'channel_follower_count': int,
            'channel_id': 'UCYO_jab_esuFRV4b17AJtAw',
            'channel': '3Blue1Brown',
            'channel_url': 'https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw',
            'description': 'md5:602e3789e6a0cb7d9d352186b720e395',
            'uploader_url': 'https://www.youtube.com/@3blue1brown',
            'uploader_id': '@3blue1brown',
            'uploader': '3Blue1Brown',
            'channel_is_verified': True,
        },
        'playlist_count': 0,
    }, {
        # Podcasts tab, with rich entry lockupViewModel
        'url': 'https://www.youtube.com/@99percentinvisiblepodcast/podcasts',
        'info_dict': {
            'id': 'UCVMF2HD4ZgC0QHpU9Yq5Xrw',
            'channel_id': 'UCVMF2HD4ZgC0QHpU9Yq5Xrw',
            'uploader_url': 'https://www.youtube.com/@99percentinvisiblepodcast',
            'description': 'md5:3a0ed38f1ad42a68ef0428c04a15695c',
            'title': '99% Invisible - Podcasts',
            'uploader': '99% Invisible',
            'channel_follower_count': int,
            'channel_url': 'https://www.youtube.com/channel/UCVMF2HD4ZgC0QHpU9Yq5Xrw',
            'tags': [],
            'channel': '99% Invisible',
            'uploader_id': '@99percentinvisiblepodcast',
        },
        'playlist_count': 5,
    }, {
        # Releases tab, with rich entry playlistRenderers (same as Podcasts tab)
        # TODO: fix channel_is_verified extraction
        'url': 'https://www.youtube.com/@AHimitsu/releases',
        'info_dict': {
            'id': 'UCgFwu-j5-xNJml2FtTrrB3A',
            'channel': 'A Himitsu',
            'uploader_url': 'https://www.youtube.com/@AHimitsu',
            'title': 'A Himitsu - Releases',
            'uploader_id': '@AHimitsu',
            'uploader': 'A Himitsu',
            'channel_id': 'UCgFwu-j5-xNJml2FtTrrB3A',
            'tags': 'count:12',
            'description': 'Music producer, sometimes.',
            'channel_url': 'https://www.youtube.com/channel/UCgFwu-j5-xNJml2FtTrrB3A',
            'channel_follower_count': int,
            'channel_is_verified': True,
        },
        'playlist_mincount': 10,
    }, {
        # Playlist with only shorts, shown as reel renderers
        # FIXME: future: YouTube currently doesn't give continuation for this,
        # may do in future.
        'url': 'https://www.youtube.com/playlist?list=UUxqPAgubo4coVn9Lx1FuKcg',
        'info_dict': {
            'id': 'UUxqPAgubo4coVn9Lx1FuKcg',
            'channel_url': 'https://www.youtube.com/channel/UCxqPAgubo4coVn9Lx1FuKcg',
            'view_count': int,
            'uploader_id': '@BangyShorts',
            'description': '',
            'uploader_url': 'https://www.youtube.com/@BangyShorts',
            'channel_id': 'UCxqPAgubo4coVn9Lx1FuKcg',
            'channel': 'Bangy Shorts',
            'uploader': 'Bangy Shorts',
            'tags': [],
            'availability': 'public',
            'modified_date': r're:\d{8}',
            'title': 'Uploads from Bangy Shorts',
        },
        'playlist_mincount': 100,
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        # TODO: fix channel_is_verified extraction
        'note': 'Tags containing spaces',
        'url': 'https://www.youtube.com/channel/UC7_YxT-KID8kRbqZo7MyscQ',
        'playlist_count': 3,
        'info_dict': {
            'id': 'UC7_YxT-KID8kRbqZo7MyscQ',
            'channel': 'Markiplier',
            'channel_id': 'UC7_YxT-KID8kRbqZo7MyscQ',
            'title': 'Markiplier',
            'channel_follower_count': int,
            'description': 'md5:0c010910558658824402809750dc5d97',
            'uploader_id': '@markiplier',
            'uploader_url': 'https://www.youtube.com/@markiplier',
            'uploader': 'Markiplier',
            'channel_url': 'https://www.youtube.com/channel/UC7_YxT-KID8kRbqZo7MyscQ',
            'channel_is_verified': True,
            'tags': ['markiplier', 'comedy', 'gaming', 'funny videos', 'funny moments',
                     'sketch comedy', 'laughing', 'lets play', 'challenge videos', 'hilarious',
                     'challenges', 'sketches', 'scary games', 'funny games', 'rage games',
                     'mark fischbach'],
        },
    }, {
        # https://github.com/yt-dlp/yt-dlp/issues/12933
        'note': 'streams tab, some scheduled streams. Empty intermediate response with only continuation - must follow',
        'url': 'https://www.youtube.com/@sbcitygov/streams',
        'playlist_mincount': 150,
        'info_dict': {
            'id': 'UCH6-qfQwlUgz9SAf05jvc_w',
            'channel': 'sbcitygov',
            'channel_id': 'UCH6-qfQwlUgz9SAf05jvc_w',
            'title': 'sbcitygov - Live',
            'channel_follower_count': int,
            'description': 'md5:ca1a92059835c071e33b3db52f4a6d67',
            'uploader_id': '@sbcitygov',
            'uploader_url': 'https://www.youtube.com/@sbcitygov',
            'uploader': 'sbcitygov',
            'channel_url': 'https://www.youtube.com/channel/UCH6-qfQwlUgz9SAf05jvc_w',
            'tags': [],
        },
    }]

    @classmethod
    def suitable(cls, url):
        return False if YoutubeIE.suitable(url) else super().suitable(url)

    _URL_RE = re.compile(rf'(?P<pre>{_VALID_URL})(?(not_channel)|(?P<tab>/[^?#/]+))?(?P<post>.*)$')

    def _get_url_mobj(self, url):
        mobj = self._URL_RE.match(url).groupdict()
        mobj.update((k, '') for k, v in mobj.items() if v is None)
        return mobj

    def _extract_tab_id_and_name(self, tab, base_url='https://www.youtube.com'):
        tab_name = (tab.get('title') or '').lower()
        tab_url = urljoin(base_url, traverse_obj(
            tab, ('endpoint', 'commandMetadata', 'webCommandMetadata', 'url')))

        tab_id = ((tab_url and self._get_url_mobj(tab_url)['tab'][1:])
                  or traverse_obj(tab, 'tabIdentifier', expected_type=str))
        if tab_id:
            return {
                'TAB_ID_SPONSORSHIPS': 'membership',
            }.get(tab_id, tab_id), tab_name

        # Fallback to tab name if we cannot get the tab id.
        # XXX: should we strip non-ascii letters? e.g. in case of 'let's play' tab example on special gaming channel
        # Note that in the case of translated tab name this may result in an empty string, which we don't want.
        if tab_name:
            self.write_debug(f'Falling back to selected tab name: {tab_name}')
        return {
            'home': 'featured',
            'live': 'streams',
        }.get(tab_name, tab_name), tab_name

    def _has_tab(self, tabs, tab_id):
        return any(self._extract_tab_id_and_name(tab)[0] == tab_id for tab in tabs)

    def _empty_playlist(self, item_id, data):
        return self.playlist_result([], item_id, **self._extract_metadata_from_tabs(item_id, data))

    @YoutubeTabBaseInfoExtractor.passthrough_smuggled_data
    def _real_extract(self, url, smuggled_data):
        item_id = self._match_id(url)
        url = urllib.parse.urlunparse(
            urllib.parse.urlparse(url)._replace(netloc='www.youtube.com'))
        compat_opts = self.get_param('compat_opts', [])

        mobj = self._get_url_mobj(url)
        pre, tab, post, is_channel = mobj['pre'], mobj['tab'], mobj['post'], not mobj['not_channel']
        if is_channel and smuggled_data.get('is_music_url'):
            if item_id[:2] == 'VL':  # Youtube music VL channels have an equivalent playlist
                return self.url_result(
                    f'https://music.youtube.com/playlist?list={item_id[2:]}', YoutubeTabIE, item_id[2:])
            elif item_id[:2] == 'MP':  # Resolve albums (/[channel/browse]/MP...) to their equivalent playlist
                mdata = self._extract_tab_endpoint(
                    f'https://music.youtube.com/channel/{item_id}', item_id, default_client='web_music')
                murl = traverse_obj(mdata, ('microformat', 'microformatDataRenderer', 'urlCanonical'),
                                    get_all=False, expected_type=str)
                if not murl:
                    raise ExtractorError('Failed to resolve album to playlist')
                return self.url_result(murl, YoutubeTabIE)
            elif mobj['channel_type'] == 'browse':  # Youtube music /browse/ should be changed to /channel/
                return self.url_result(
                    f'https://music.youtube.com/channel/{item_id}{tab}{post}', YoutubeTabIE, item_id)

        original_tab_id, display_id = tab[1:], f'{item_id}{tab}'
        if is_channel and not tab and 'no-youtube-channel-redirect' not in compat_opts:
            url = f'{pre}/videos{post}'
        if smuggled_data.get('is_music_url'):
            self.report_warning(f'YouTube Music is not directly supported. Redirecting to {url}')

        # Handle both video/playlist URLs
        qs = parse_qs(url)
        video_id, playlist_id = (traverse_obj(qs, (key, 0)) for key in ('v', 'list'))
        if not video_id and mobj['not_channel'].startswith('watch'):
            if not playlist_id:
                # If there is neither video or playlist ids, youtube redirects to home page, which is undesirable
                raise ExtractorError('A video URL was given without video ID', expected=True)
            # Common mistake: https://www.youtube.com/watch?list=playlist_id
            self.report_warning(f'A video URL was given without video ID. Trying to download playlist {playlist_id}')
            return self.url_result(
                f'https://www.youtube.com/playlist?list={playlist_id}', YoutubeTabIE, playlist_id)

        if not self._yes_playlist(playlist_id, video_id):
            return self.url_result(
                f'https://www.youtube.com/watch?v={video_id}', YoutubeIE, video_id)

        data, ytcfg = self._extract_data(url, display_id)

        # YouTube may provide a non-standard redirect to the regional channel
        # See: https://github.com/yt-dlp/yt-dlp/issues/2694
        # https://support.google.com/youtube/answer/2976814#zippy=,conditional-redirects
        redirect_url = traverse_obj(
            data, ('onResponseReceivedActions', ..., 'navigateAction', 'endpoint', 'commandMetadata', 'webCommandMetadata', 'url'), get_all=False)
        if redirect_url and 'no-youtube-channel-redirect' not in compat_opts:
            redirect_url = ''.join((urljoin('https://www.youtube.com', redirect_url), tab, post))
            self.to_screen(f'This playlist is likely not available in your region. Following conditional redirect to {redirect_url}')
            return self.url_result(redirect_url, YoutubeTabIE)

        tabs, extra_tabs = self._extract_tab_renderers(data), []
        if is_channel and tabs and 'no-youtube-channel-redirect' not in compat_opts:
            selected_tab = self._extract_selected_tab(tabs)
            selected_tab_id, selected_tab_name = self._extract_tab_id_and_name(selected_tab, url)  # NB: Name may be translated
            self.write_debug(f'Selected tab: {selected_tab_id!r} ({selected_tab_name}), Requested tab: {original_tab_id!r}')

            # /about is no longer a tab
            if original_tab_id == 'about':
                return self._empty_playlist(item_id, data)

            if not original_tab_id and selected_tab_name:
                self.to_screen('Downloading all uploads of the channel. '
                               'To download only the videos in a specific tab, pass the tab\'s URL')
                if self._has_tab(tabs, 'streams'):
                    extra_tabs.append(''.join((pre, '/streams', post)))
                if self._has_tab(tabs, 'shorts'):
                    extra_tabs.append(''.join((pre, '/shorts', post)))
                # XXX: Members-only tab should also be extracted

                if not extra_tabs and selected_tab_id != 'videos':
                    # Channel does not have streams, shorts or videos tabs
                    if item_id[:2] != 'UC':
                        return self._empty_playlist(item_id, data)

                    # Topic channels don't have /videos. Use the equivalent playlist instead
                    pl_id = f'UU{item_id[2:]}'
                    pl_url = f'https://www.youtube.com/playlist?list={pl_id}'
                    try:
                        data, ytcfg = self._extract_data(pl_url, pl_id, ytcfg=ytcfg, fatal=True, webpage_fatal=True)
                    except ExtractorError:
                        return self._empty_playlist(item_id, data)
                    else:
                        item_id, url = pl_id, pl_url
                        self.to_screen(
                            f'The channel does not have a videos, shorts, or live tab. Redirecting to playlist {pl_id} instead')

                elif extra_tabs and selected_tab_id != 'videos':
                    # When there are shorts/live tabs but not videos tab
                    url, data = f'{pre}{post}', None

            elif (original_tab_id or 'videos') != selected_tab_id:
                if original_tab_id == 'live':
                    # Live tab should have redirected to the video
                    # Except in the case the channel has an actual live tab
                    # Example: https://www.youtube.com/channel/UCEH7P7kyJIkS_gJf93VYbmg/live
                    raise UserNotLive(video_id=item_id)
                elif selected_tab_name:
                    raise ExtractorError(f'This channel does not have a {original_tab_id} tab', expected=True)

                # For channels such as https://www.youtube.com/channel/UCtFRv9O2AHqOZjjynzrv-xg
                url = f'{pre}{post}'

        # YouTube sometimes provides a button to reload playlist with unavailable videos.
        if 'no-youtube-unavailable-videos' not in compat_opts:
            data = self._reload_with_unavailable_videos(display_id, data, ytcfg) or data
        self._extract_and_report_alerts(data, only_once=True)

        tabs, entries = self._extract_tab_renderers(data), []
        if tabs:
            entries = [self._extract_from_tabs(item_id, ytcfg, data, tabs)]
            entries[0].update({
                'extractor_key': YoutubeTabIE.ie_key(),
                'extractor': YoutubeTabIE.IE_NAME,
                'webpage_url': url,
            })
        if self.get_param('playlist_items') == '0':
            entries.extend(self.url_result(u, YoutubeTabIE) for u in extra_tabs)
        else:  # Users expect to get all `video_id`s even with `--flat-playlist`. So don't return `url_result`
            entries.extend(map(self._real_extract, extra_tabs))

        if len(entries) == 1:
            return entries[0]
        elif entries:
            metadata = self._extract_metadata_from_tabs(item_id, data)
            uploads_url = 'the Uploads (UU) playlist URL'
            if try_get(metadata, lambda x: x['channel_id'].startswith('UC')):
                uploads_url = f'https://www.youtube.com/playlist?list=UU{metadata["channel_id"][2:]}'
            self.to_screen(
                'Downloading as multiple playlists, separated by tabs. '
                f'To download as a single playlist instead, pass {uploads_url}')
            return self.playlist_result(entries, item_id, **metadata)

        # Inline playlist
        playlist = traverse_obj(
            data, ('contents', 'twoColumnWatchNextResults', 'playlist', 'playlist'), expected_type=dict)
        if playlist:
            return self._extract_from_playlist(item_id, url, data, playlist, ytcfg)

        video_id = traverse_obj(
            data, ('currentVideoEndpoint', 'watchEndpoint', 'videoId'), expected_type=str) or video_id
        if video_id:
            if tab != '/live':  # live tab is expected to redirect to video
                self.report_warning(f'Unable to recognize playlist. Downloading just video {video_id}')
            return self.url_result(f'https://www.youtube.com/watch?v={video_id}', YoutubeIE, video_id)

        raise ExtractorError('Unable to recognize tab page')


# xxx: This is tightly coupled to YoutubeTabBaseInfoExtractor. Should be decoupled at some point
class YoutubePlaylistIE(YoutubeBaseInfoExtractor):
    IE_DESC = 'YouTube playlists'
    _VALID_URL = r'''(?x)(?:
                        (?:https?://)?
                        (?:\w+\.)?
                        (?:
                            (?:
                                youtube(?:kids)?\.com|
                                {invidious}
                            )
                            /.*?\?.*?\blist=
                        )?
                        (?P<id>{playlist_id})
                     )'''.format(
        playlist_id=YoutubeBaseInfoExtractor._PLAYLIST_ID_RE,
        invidious='|'.join(YoutubeBaseInfoExtractor._INVIDIOUS_SITES),
    )
    IE_NAME = 'youtube:playlist'
    _TESTS = [{
        # TODO: fix availability extraction
        'note': 'issue #673',
        'url': 'PLBB231211A4F62143',
        'info_dict': {
            'title': 'Team Fortress 2 [2010 Version]',
            'id': 'PLBB231211A4F62143',
            'uploader': 'Wickman Wish',
            'uploader_id': '@WickmanWish',
            'description': 'md5:8fa6f52abb47a9552002fa3ddfc57fc2',
            'view_count': int,
            'uploader_url': 'https://www.youtube.com/@WickmanWish',
            'modified_date': r're:\d{8}',
            'channel_id': 'UCKSpbfbl5kRQpTdL7kMc-1Q',
            'channel': 'Wickman Wish',
            'tags': [],
            'channel_url': 'https://www.youtube.com/channel/UCKSpbfbl5kRQpTdL7kMc-1Q',
            'availability': 'public',
        },
        'playlist_mincount': 29,
    }, {
        'url': 'PLtPgu7CB4gbY9oDN3drwC3cMbJggS7dKl',
        'info_dict': {
            'title': 'YDL_safe_search',
            'id': 'PLtPgu7CB4gbY9oDN3drwC3cMbJggS7dKl',
        },
        'playlist_count': 2,
        'skip': 'This playlist is private',
    }, {
        # TODO: fix availability extraction
        'note': 'embedded',
        'url': 'https://www.youtube.com/embed/videoseries?list=PL6IaIsEjSbf96XFRuNccS_RuEXwNdsoEu',
        'playlist_count': 4,
        'info_dict': {
            'title': 'JODA15',
            'id': 'PL6IaIsEjSbf96XFRuNccS_RuEXwNdsoEu',
            'uploader': 'milan',
            'uploader_id': '@milan5503',
            'description': '',
            'channel_url': 'https://www.youtube.com/channel/UCEI1-PVPcYXjB73Hfelbmaw',
            'tags': [],
            'modified_date': '20140919',
            'view_count': int,
            'channel': 'milan',
            'channel_id': 'UCEI1-PVPcYXjB73Hfelbmaw',
            'uploader_url': 'https://www.youtube.com/@milan5503',
            'availability': 'public',
        },
        'expected_warnings': [r'[Uu]navailable videos? (is|are|will be) hidden', 'Retrying', 'Giving up'],
    }, {
        # TODO: fix availability extraction
        'url': 'http://www.youtube.com/embed/_xDOZElKyNU?list=PLsyOSbh5bs16vubvKePAQ1x3PhKavfBIl',
        'playlist_mincount': 455,
        'info_dict': {
            'title': '2018 Chinese New Singles (11/6 updated)',
            'id': 'PLsyOSbh5bs16vubvKePAQ1x3PhKavfBIl',
            'uploader': 'LBK',
            'uploader_id': '@music_king',
            'description': 'md5:da521864744d60a198e3a88af4db0d9d',
            'channel': 'LBK',
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UC21nz3_MesPLqtDqwdvnoxA',
            'tags': [],
            'uploader_url': 'https://www.youtube.com/@music_king',
            'channel_id': 'UC21nz3_MesPLqtDqwdvnoxA',
            'modified_date': r're:\d{8}',
            'availability': 'public',
        },
        'expected_warnings': [r'[Uu]navailable videos (are|will be) hidden'],
    }, {
        'url': 'TLGGrESM50VT6acwMjAyMjAxNw',
        'only_matching': True,
    }, {
        # music album playlist
        'url': 'OLAK5uy_m4xAFdmMC5rX3Ji3g93pQe3hqLZw_9LhM',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        if YoutubeTabIE.suitable(url):
            return False
        from yt_dlp.utils import parse_qs
        qs = parse_qs(url)
        if qs.get('v', [None])[0]:
            return False
        return super().suitable(url)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        is_music_url = YoutubeBaseInfoExtractor.is_music_url(url)
        url = update_url_query(
            'https://www.youtube.com/playlist',
            parse_qs(url) or {'list': playlist_id})
        if is_music_url:
            url = smuggle_url(url, {'is_music_url': True})
        return self.url_result(url, ie=YoutubeTabIE.ie_key(), video_id=playlist_id)
