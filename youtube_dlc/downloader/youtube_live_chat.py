from __future__ import division, unicode_literals

import re
import json

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

        def dl_fragment(url):
            headers = info_dict.get('http_headers', {})
            return self._download_fragment(ctx, url, info_dict, headers)

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

        def download_and_parse_fragment(url, frag_index):
            count = 0
            while count <= fragment_retries:
                try:
                    success, raw_fragment = dl_fragment(url)
                    if not success:
                        return False, None, None
                    data = parse_yt_initial_data(raw_fragment) or json.loads(raw_fragment)['response']

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

        frag_index = offset = 0
        while continuation_id is not None:
            frag_index += 1
            url = ''.join((
                'https://www.youtube.com/live_chat_replay',
                '/get_live_chat_replay' if frag_index > 1 else '',
                '?continuation=%s' % continuation_id,
                '&playerOffsetMs=%d&hidden=false&pbj=1' % max(offset - 5000, 0) if frag_index > 1 else ''))
            success, continuation_id, offset = download_and_parse_fragment(url, frag_index)
            if not success:
                return False
            if test:
                break

        self._finish_frag_download(ctx)
        return True
