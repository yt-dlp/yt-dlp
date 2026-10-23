import itertools
import re

from ._tab import YoutubeTabBaseInfoExtractor, YoutubeTabIE
from ._video import YoutubeIE
from ...utils import traverse_obj


class YoutubeNotificationsIE(YoutubeTabBaseInfoExtractor):
    IE_NAME = 'youtube:notif'
    IE_DESC = 'YouTube notifications; ":ytnotif" keyword (requires cookies)'
    _VALID_URL = r':ytnotif(?:ication)?s?'
    _LOGIN_REQUIRED = True
    _TESTS = [{
        'url': ':ytnotif',
        'only_matching': True,
    }, {
        'url': ':ytnotifications',
        'only_matching': True,
    }]

    def _extract_notification_menu(self, response, continuation_list):
        notification_list = traverse_obj(
            response,
            ('actions', 0, 'openPopupAction', 'popup', 'multiPageMenuRenderer', 'sections', 0, 'multiPageMenuNotificationSectionRenderer', 'items'),
            ('actions', 0, 'appendContinuationItemsAction', 'continuationItems'),
            expected_type=list) or []
        continuation_list[0] = None
        for item in notification_list:
            entry = self._extract_notification_renderer(item.get('notificationRenderer'))
            if entry:
                yield entry
            continuation = item.get('continuationItemRenderer')
            if continuation:
                continuation_list[0] = continuation

    def _extract_notification_renderer(self, notification):
        video_id = traverse_obj(
            notification, ('navigationEndpoint', 'watchEndpoint', 'videoId'), expected_type=str)
        url = f'https://www.youtube.com/watch?v={video_id}'
        channel_id = None
        if not video_id:
            browse_ep = traverse_obj(
                notification, ('navigationEndpoint', 'browseEndpoint'), expected_type=dict)
            channel_id = self.ucid_or_none(traverse_obj(browse_ep, 'browseId', expected_type=str))
            post_id = self._search_regex(
                r'/post/(.+)', traverse_obj(browse_ep, 'canonicalBaseUrl', expected_type=str),
                'post id', default=None)
            if not channel_id or not post_id:
                return
            # The direct /post url redirects to this in the browser
            url = f'https://www.youtube.com/channel/{channel_id}/community?lb={post_id}'

        channel = traverse_obj(
            notification, ('contextualMenu', 'menuRenderer', 'items', 1, 'menuServiceItemRenderer', 'text', 'runs', 1, 'text'),
            expected_type=str)
        notification_title = self._get_text(notification, 'shortMessage')
        if notification_title:
            notification_title = notification_title.replace('\xad', '')  # remove soft hyphens
        # TODO: handle recommended videos
        title = self._search_regex(
            rf'{re.escape(channel or "")}[^:]+: (.+)', notification_title,
            'video title', default=None)
        timestamp = (self._parse_time_text(self._get_text(notification, 'sentTimeText'))
                     if self._configuration_arg('approximate_date', ie_key=YoutubeTabIE)
                     else None)
        return {
            '_type': 'url',
            'url': url,
            'ie_key': (YoutubeIE if video_id else YoutubeTabIE).ie_key(),
            'video_id': video_id,
            'title': title,
            'channel_id': channel_id,
            'channel': channel,
            'uploader': channel,
            'thumbnails': self._extract_thumbnails(notification, 'videoThumbnail'),
            'timestamp': timestamp,
        }

    def _notification_menu_entries(self, ytcfg):
        continuation_list = [None]
        response = None
        for page in itertools.count(1):
            ctoken = traverse_obj(
                continuation_list, (0, 'continuationEndpoint', 'getNotificationMenuEndpoint', 'ctoken'), expected_type=str)
            response = self._extract_response(
                item_id=f'page {page}', query={'ctoken': ctoken} if ctoken else {}, ytcfg=ytcfg,
                ep='notification/get_notification_menu', check_get_keys='actions',
                headers=self.generate_api_headers(ytcfg=ytcfg, visitor_data=self._extract_visitor_data(response)))
            yield from self._extract_notification_menu(response, continuation_list)
            if not continuation_list[0]:
                break

    def _real_extract(self, url):
        display_id = 'notifications'
        ytcfg = self._download_ytcfg('web', display_id) if not self.skip_webpage else {}
        self._report_playlist_authcheck(ytcfg)
        return self.playlist_result(self._notification_menu_entries(ytcfg), display_id, display_id)
