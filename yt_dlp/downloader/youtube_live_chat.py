from __future__ import division, unicode_literals

import json

from .fragment import FragmentFD
from ..compat import compat_urllib_error
from ..utils import (
    try_get,
    RegexNotFoundError,
)
from ..extractor.youtube import YoutubeBaseInfoExtractor as YT_BaseIE


class YoutubeLiveChatReplayFD(FragmentFD):
    """ Downloads YouTube live chat replays fragment by fragment """

    FD_NAME = 'youtube_live_chat_replay'

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

        def dl_fragment(url, data=None, headers=None):
            http_headers = info_dict.get('http_headers', {})
            if headers:
                http_headers = http_headers.copy()
                http_headers.update(headers)
            return self._download_fragment(ctx, url, info_dict, http_headers, data)

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
        url = 'https://www.youtube.com/youtubei/v1/live_chat/get_live_chat_replay?key=' + api_key

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
