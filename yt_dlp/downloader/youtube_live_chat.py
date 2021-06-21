from __future__ import division, unicode_literals

import json
import time

from .fragment import FragmentFD
from ..compat import compat_urllib_error
from ..utils import (
    try_get,
    RegexNotFoundError,
)
from ..extractor.youtube import YoutubeBaseInfoExtractor as YT_BaseIE


class YoutubeLiveChatFD(FragmentFD):
    """ Downloads YouTube live chats fragment by fragment """

    FD_NAME = 'youtube_live_chat'

    def real_download(self, filename, info_dict):
        video_id = info_dict['video_id']
        self.to_screen('[%s] Downloading live chat' % self.FD_NAME)

        fragment_retries = self.params.get('fragment_retries', 0)
        test = self.params.get('test', False)

        ctx = {
            'filename': filename,
            'live': True,
            'total_frags': None,
        }

        ie = YT_BaseIE(self.ydl)

        start_time = int(time.time() * 1000)

        def dl_fragment(url, data=None, headers=None):
            http_headers = info_dict.get('http_headers', {})
            if headers:
                http_headers = http_headers.copy()
                http_headers.update(headers)
            return self._download_fragment(ctx, url, info_dict, http_headers, data)

        def parse_actions_replay(live_chat_continuation):
            offset = continuation_id = None
            processed_fragment = bytearray()
            for action in live_chat_continuation.get('actions', []):
                if 'replayChatItemAction' in action:
                    replay_chat_item_action = action['replayChatItemAction']
                    offset = int(replay_chat_item_action['videoOffsetTimeMsec'])
                processed_fragment.extend(
                    json.dumps(action, ensure_ascii=False).encode('utf-8') + b'\n')
            if offset is not None:
                continuation_id = try_get(
                    live_chat_continuation,
                    lambda x: x['continuations'][0]['liveChatReplayContinuationData']['continuation'])
            self._append_fragment(ctx, processed_fragment)
            return continuation_id, offset

        def parse_live_timestamp(action):
            action_content = (
                try_get(action, lambda x: x['addChatItemAction'], dict)
                or try_get(action, lambda x: x['addLiveChatTickerItemAction'], dict)
                or try_get(action, lambda x: x['addBannerToLiveChatCommand'], dict)
            )
            if action_content is None or type(action_content) != dict:
                return None
            item = (
                try_get(action_content, lambda x: x['item'], dict)
                or try_get(action_content, lambda x: x['bannerRenderer'], dict)
            )
            if item is None:
                return None
            renderer = (
                # text
                try_get(item, lambda x: x['liveChatTextMessageRenderer'], dict)
                or try_get(item, lambda x: x['liveChatPaidMessageRenderer'], dict)
                or try_get(item, lambda x: x['liveChatMembershipItemRenderer'], dict)
                or try_get(item, lambda x: x['liveChatPaidStickerRenderer'], dict)
                # ticker
                or try_get(item, lambda x: x['liveChatTickerPaidMessageItemRenderer'], dict)
                or try_get(item, lambda x: x['liveChatTickerSponsorItemRenderer'], dict)
                # banner
                or try_get(item, lambda x: x['liveChatBannerRenderer'], dict)
            )
            if renderer is None:
                return None
            parent_item = (
                try_get(
                    renderer,
                    lambda x: x['showItemEndpoint']['showLiveChatItemEndpoint']['renderer'], dict)
                or try_get(renderer, lambda x: x['contents'], dict)
            )
            if parent_item:
                renderer = (
                    try_get(parent_item, lambda x: x['liveChatTextMessageRenderer'], dict)
                    or try_get(parent_item, lambda x: x['liveChatPaidMessageRenderer'], dict)
                    or try_get(parent_item, lambda x: x['liveChatMembershipItemRenderer'], dict)
                    or try_get(parent_item, lambda x: x['liveChatPaidStickerRenderer'], dict)
                )
            if renderer:
                timestamp_usec = try_get(renderer, lambda x: x['timestampUsec'], str)
                if timestamp_usec:
                    return int(int(timestamp_usec) / 1000)
            return None

        live_offset = 0

        def parse_actions_live(live_chat_continuation):
            nonlocal live_offset
            continuation_id = None
            processed_fragment = bytearray()
            for action in live_chat_continuation.get('actions', []):
                timestamp = parse_live_timestamp(action)
                if timestamp is not None:
                    live_offset = timestamp - start_time
                # compatibility with replay format
                pseudo_action = {
                    'replayChatItemAction': {'actions': [action]},
                    'videoOffsetTimeMsec': str(live_offset),
                    'isLive': True,
                }
                processed_fragment.extend(
                    json.dumps(pseudo_action, ensure_ascii=False).encode('utf-8') + b'\n')
            continuation_data = (
                try_get(
                    live_chat_continuation,
                    lambda x: x['continuations'][0]['invalidationContinuationData'], dict)
                or try_get(
                    live_chat_continuation,
                    lambda x: x['continuations'][0]['timedContinuationData'], dict)
            )
            if continuation_data:
                continuation_id = try_get(continuation_data, lambda x: x['continuation'])
                timeout_ms = try_get(continuation_data, lambda x: x['timeoutMs'])
                if timeout_ms is not None:
                    time.sleep(int(timeout_ms) / 1000)
            self._append_fragment(ctx, processed_fragment)
            return continuation_id, live_offset

        if info_dict['protocol'] == 'youtube_live_chat_replay':
            parse_actions = parse_actions_replay
        elif info_dict['protocol'] == 'youtube_live_chat':
            parse_actions = parse_actions_live

        def download_and_parse_fragment(url, frag_index, request_data):
            count = 0
            while count <= fragment_retries:
                try:
                    success, raw_fragment = dl_fragment(url, request_data, {'content-type': 'application/json'})
                    if not success:
                        return False, None, None
                    try:
                        data = ie._extract_yt_initial_data(video_id, raw_fragment.decode('utf-8', 'replace'))
                    except RegexNotFoundError:
                        data = None
                    if not data:
                        data = json.loads(raw_fragment)
                    live_chat_continuation = try_get(
                        data,
                        lambda x: x['continuationContents']['liveChatContinuation'], dict) or {}
                    continuation_id, offset = parse_actions(live_chat_continuation)
                    return True, continuation_id, offset
                except compat_urllib_error.HTTPError as err:
                    count += 1
                    if count <= fragment_retries:
                        self.report_retry_fragment(err, frag_index, count, fragment_retries)
            if count > fragment_retries:
                self.report_error('giving up after %s fragment retries' % fragment_retries)
                return False, None, None

        self._prepare_and_start_frag_download(ctx)

        success, raw_fragment = dl_fragment(info_dict['url'])
        if not success:
            return False
        try:
            data = ie._extract_yt_initial_data(video_id, raw_fragment.decode('utf-8', 'replace'))
        except RegexNotFoundError:
            return False
        continuation_id = try_get(
            data,
            lambda x: x['contents']['twoColumnWatchNextResults']['conversationBar']['liveChatRenderer']['continuations'][0]['reloadContinuationData']['continuation'])
        # no data yet but required to call _append_fragment
        self._append_fragment(ctx, b'')

        ytcfg = ie._extract_ytcfg(video_id, raw_fragment.decode('utf-8', 'replace'))

        if not ytcfg:
            return False
        api_key = try_get(ytcfg, lambda x: x['INNERTUBE_API_KEY'])
        innertube_context = try_get(ytcfg, lambda x: x['INNERTUBE_CONTEXT'])
        if not api_key or not innertube_context:
            return False
        if info_dict['protocol'] == 'youtube_live_chat_replay':
            url = 'https://www.youtube.com/youtubei/v1/live_chat/get_live_chat_replay?key=' + api_key
        elif info_dict['protocol'] == 'youtube_live_chat':
            url = 'https://www.youtube.com/youtubei/v1/live_chat/get_live_chat?key=' + api_key

        frag_index = offset = 0
        while continuation_id is not None:
            frag_index += 1
            request_data = {
                'context': innertube_context,
                'continuation': continuation_id,
            }
            if frag_index > 1:
                request_data['currentPlayerState'] = {'playerOffsetMs': str(max(offset - 5000, 0))}
            success, continuation_id, offset = download_and_parse_fragment(
                url, frag_index, json.dumps(request_data, ensure_ascii=False).encode('utf-8') + b'\n')
            if not success:
                return False
            if test:
                break

        self._finish_frag_download(ctx)
        return True
