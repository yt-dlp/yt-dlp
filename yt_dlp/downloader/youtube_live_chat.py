import json
import time

from .fragment import FragmentFD
from ..networking.exceptions import HTTPError
from ..utils import (
    RegexNotFoundError,
    RetryManager,
    dict_get,
    int_or_none,
    try_get,
)
from ..utils.networking import HTTPHeaderDict


class YoutubeLiveChatFD(FragmentFD):
    """ Downloads YouTube live chats fragment by fragment """

    def real_download(self, filename, info_dict):
        video_id = info_dict['video_id']
        self.to_screen(f'[{self.FD_NAME}] Downloading live chat')
        if not self.params.get('skip_download') and info_dict['protocol'] == 'youtube_live_chat':
            self.report_warning('Live chat download runs until the livestream ends. '
                                'If you wish to download the video simultaneously, run a separate yt-dlp instance')

        test = self.params.get('test', False)

        ctx = {
            'filename': filename,
            'live': True,
            'total_frags': None,
        }

        from ..extractor.youtube import YoutubeBaseInfoExtractor

        ie = YoutubeBaseInfoExtractor(self.ydl)

        start_time = int(time.time() * 1000)

        def dl_fragment(url, data=None, headers=None):
            http_headers = HTTPHeaderDict(info_dict.get('http_headers'), headers)
            return self._download_fragment(ctx, url, info_dict, http_headers, data)

        def parse_actions_replay(live_chat_continuation):
            offset = continuation_id = click_tracking_params = None
            processed_fragment = bytearray()
            for action in live_chat_continuation.get('actions', []):
                if 'replayChatItemAction' in action:
                    replay_chat_item_action = action['replayChatItemAction']
                    offset = int(replay_chat_item_action['videoOffsetTimeMsec'])
                processed_fragment.extend(
                    json.dumps(action, ensure_ascii=False).encode() + b'\n')
            if offset is not None:
                continuation = try_get(
                    live_chat_continuation,
                    lambda x: x['continuations'][0]['liveChatReplayContinuationData'], dict)
                if continuation:
                    continuation_id = continuation.get('continuation')
                    click_tracking_params = continuation.get('clickTrackingParams')
            self._append_fragment(ctx, processed_fragment)
            return continuation_id, offset, click_tracking_params

        def try_refresh_replay_beginning(live_chat_continuation):
            # choose the second option that contains the unfiltered live chat replay
            refresh_continuation = try_get(
                live_chat_continuation,
                lambda x: x['header']['liveChatHeaderRenderer']['viewSelector']['sortFilterSubMenuRenderer']['subMenuItems'][1]['continuation']['reloadContinuationData'], dict)
            if refresh_continuation:
                # no data yet but required to call _append_fragment
                self._append_fragment(ctx, b'')
                refresh_continuation_id = refresh_continuation.get('continuation')
                offset = 0
                click_tracking_params = refresh_continuation.get('trackingParams')
                return refresh_continuation_id, offset, click_tracking_params
            return parse_actions_replay(live_chat_continuation)

        live_offset = 0

        def parse_actions_live(live_chat_continuation):
            nonlocal live_offset
            continuation_id = click_tracking_params = None
            processed_fragment = bytearray()
            for action in live_chat_continuation.get('actions', []):
                timestamp = self.parse_live_timestamp(action)
                if timestamp is not None:
                    live_offset = timestamp - start_time
                # compatibility with replay format
                pseudo_action = {
                    'replayChatItemAction': {'actions': [action]},
                    'videoOffsetTimeMsec': str(live_offset),
                    'isLive': True,
                }
                processed_fragment.extend(
                    json.dumps(pseudo_action, ensure_ascii=False).encode() + b'\n')
            continuation_data_getters = [
                lambda x: x['continuations'][0]['invalidationContinuationData'],
                lambda x: x['continuations'][0]['timedContinuationData'],
            ]
            continuation_data = try_get(live_chat_continuation, continuation_data_getters, dict)
            if continuation_data:
                continuation_id = continuation_data.get('continuation')
                click_tracking_params = continuation_data.get('clickTrackingParams')
                timeout_ms = int_or_none(continuation_data.get('timeoutMs'))
                if timeout_ms is not None:
                    time.sleep(timeout_ms / 1000)
            self._append_fragment(ctx, processed_fragment)
            return continuation_id, live_offset, click_tracking_params

        def download_and_parse_fragment(url, frag_index, request_data=None, headers=None):
            for retry in RetryManager(self.params.get('fragment_retries'), self.report_retry, frag_index=frag_index):
                try:
                    success = dl_fragment(url, request_data, headers)
                    if not success:
                        return False, None, None, None
                    raw_fragment = self._read_fragment(ctx)
                    try:
                        data = ie.extract_yt_initial_data(video_id, raw_fragment.decode('utf-8', 'replace'))
                    except RegexNotFoundError:
                        data = None
                    if not data:
                        data = json.loads(raw_fragment)
                    live_chat_continuation = try_get(
                        data,
                        lambda x: x['continuationContents']['liveChatContinuation'], dict) or {}

                    func = ((info_dict['protocol'] == 'youtube_live_chat' and parse_actions_live)
                            or (frag_index == 1 and try_refresh_replay_beginning)
                            or parse_actions_replay)
                    return (True, *func(live_chat_continuation))
                except HTTPError as err:
                    retry.error = err
                    continue
            return False, None, None, None

        self._prepare_and_start_frag_download(ctx, info_dict)

        success = dl_fragment(info_dict['url'])
        if not success:
            return False
        raw_fragment = self._read_fragment(ctx)
        try:
            data = ie.extract_yt_initial_data(video_id, raw_fragment.decode('utf-8', 'replace'))
        except RegexNotFoundError:
            return False
        continuation_id = try_get(
            data,
            lambda x: x['contents']['twoColumnWatchNextResults']['conversationBar']['liveChatRenderer']['continuations'][0]['reloadContinuationData']['continuation'])
        # no data yet but required to call _append_fragment
        self._append_fragment(ctx, b'')

        ytcfg = ie.extract_ytcfg(video_id, raw_fragment.decode('utf-8', 'replace'))

        if not ytcfg:
            return False
        api_key = try_get(ytcfg, lambda x: x['INNERTUBE_API_KEY'])
        innertube_context = try_get(ytcfg, lambda x: x['INNERTUBE_CONTEXT'])
        if not api_key or not innertube_context:
            return False
        visitor_data = try_get(innertube_context, lambda x: x['client']['visitorData'], str)
        if info_dict['protocol'] == 'youtube_live_chat_replay':
            url = 'https://www.youtube.com/youtubei/v1/live_chat/get_live_chat_replay?key=' + api_key
            chat_page_url = 'https://www.youtube.com/live_chat_replay?continuation=' + continuation_id
        elif info_dict['protocol'] == 'youtube_live_chat':
            url = 'https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key=' + api_key
            chat_page_url = 'https://www.youtube.com/live_chat?continuation=' + continuation_id

        frag_index = offset = 0
        click_tracking_params = None
        while continuation_id is not None:
            frag_index += 1
            request_data = {
                'context': innertube_context,
                'continuation': continuation_id,
            }
            if frag_index > 1:
                request_data['currentPlayerState'] = {'playerOffsetMs': str(max(offset - 5000, 0))}
                if click_tracking_params:
                    request_data['context']['clickTracking'] = {'clickTrackingParams': click_tracking_params}
                headers = ie.generate_api_headers(ytcfg=ytcfg, visitor_data=visitor_data)
                headers.update({'content-type': 'application/json'})
                fragment_request_data = json.dumps(request_data, ensure_ascii=False).encode() + b'\n'
                success, continuation_id, offset, click_tracking_params = download_and_parse_fragment(
                    url, frag_index, fragment_request_data, headers)
            else:
                success, continuation_id, offset, click_tracking_params = download_and_parse_fragment(
                    chat_page_url, frag_index)
            if not success:
                return False
            if test:
                break

        return self._finish_frag_download(ctx, info_dict)

    @staticmethod
    def parse_live_timestamp(action):
        action_content = dict_get(
            action,
            ['addChatItemAction', 'addLiveChatTickerItemAction', 'addBannerToLiveChatCommand'])
        if not isinstance(action_content, dict):
            return None
        item = dict_get(action_content, ['item', 'bannerRenderer'])
        if not isinstance(item, dict):
            return None
        renderer = dict_get(item, [
            # text
            'liveChatTextMessageRenderer', 'liveChatPaidMessageRenderer',
            'liveChatMembershipItemRenderer', 'liveChatPaidStickerRenderer',
            # ticker
            'liveChatTickerPaidMessageItemRenderer',
            'liveChatTickerSponsorItemRenderer',
            # banner
            'liveChatBannerRenderer',
        ])
        if not isinstance(renderer, dict):
            return None
        parent_item_getters = [
            lambda x: x['showItemEndpoint']['showLiveChatItemEndpoint']['renderer'],
            lambda x: x['contents'],
        ]
        parent_item = try_get(renderer, parent_item_getters, dict)
        if parent_item:
            renderer = dict_get(parent_item, [
                'liveChatTextMessageRenderer', 'liveChatPaidMessageRenderer',
                'liveChatMembershipItemRenderer', 'liveChatPaidStickerRenderer',
            ])
            if not isinstance(renderer, dict):
                return None
        return int_or_none(renderer.get('timestampUsec'), 1000)
