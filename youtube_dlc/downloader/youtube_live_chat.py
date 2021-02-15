from __future__ import division, unicode_literals

import re
import json
import copy

from .fragment import FragmentFD
from ..compat import compat_urllib_error
from ..utils import try_get
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

        def dl_fragment(url, data=None, headers=None):
            http_headers = info_dict.get('http_headers', {})
            if headers:
                http_headers = copy.deepcopy(http_headers)
                http_headers.update(headers)
            return self._download_fragment(ctx, url, info_dict, http_headers, data)

        def parse_yt_initial_data(data):
            patterns = (
                r'%s\\s*%s' % (YT_BaseIE._YT_INITIAL_DATA_RE, YT_BaseIE._YT_INITIAL_BOUNDARY_RE),
                r'%s' % YT_BaseIE._YT_INITIAL_DATA_RE)
            data = data.decode('utf-8', 'replace')
            for patt in patterns:
                try:
                    raw_json = re.search(patt, data).group(1)
                    return json.loads(raw_json)
                except AttributeError:
                    continue

        def parse_ytcfg(data):
            data = data.decode('utf-8', 'replace')
            try:
                raw_json = re.search(r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', data).group(1)
                return json.loads(raw_json)
            except IndexError:
                return None

        def download_and_parse_fragment(url, frag_index, request_data):
            count = 0
            while count <= fragment_retries:
                try:
                    success, raw_fragment = dl_fragment(url, request_data, {'content-type': 'application/json'})
                    if not success:
                        return False, None, None
                    data = parse_yt_initial_data(raw_fragment)
                    if not data:
                        data = {}
                        raw_data = json.loads(raw_fragment)
                        # sometimes youtube replies with a list
                        if not isinstance(raw_data, list):
                            raw_data = [raw_data]
                        for item in raw_data:
                            # data is sometimes behind 'response'
                            if 'response' in item:
                                data = item['response']
                            else:
                                data = item
                            break

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

        success, raw_fragment = dl_fragment(
            'https://www.youtube.com/watch?v={}'.format(video_id))
        if not success:
            return False
        data = parse_yt_initial_data(raw_fragment)
        continuation_id = try_get(
            data,
            lambda x: x['contents']['twoColumnWatchNextResults']['conversationBar']['liveChatRenderer']['continuations'][0]['reloadContinuationData']['continuation'])
        # no data yet but required to call _append_fragment
        self._append_fragment(ctx, b'')

        ytcfg = parse_ytcfg(raw_fragment)
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
