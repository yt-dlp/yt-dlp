import datetime
import json
import re

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, traverse_obj, unified_timestamp


class PiczelIE(InfoExtractor):
    _VALID_URL = [
        r'https?://(?:www\.)(?P<host>piczel\.tv)/watch/(?P<id>[^/]+)',
        r'https?://(?P<host>piczel\.tv)/watch/(?P<id>[^/]+)',
    ]
    _TESTS = [{
        'url': 'https://piczel.tv/watch/AndrewAssassins',
        'info_dict': {
            'id': '100342',
            'formats': list,
            'title': 'Drawing Open for coms.',
            'age_limit': int,
            'uploader': 'AndrewAssassins',
            'uploader_id': 106162,
            'timestamp': 1772652096,
            'upload_date': '20260305',
            'ext': 'mp4',
            'description': 'MY prices here https://x.com/AndrewLey_AA/status/2007280230503977019?s=20',
            'tags': list,
            'concurrent_view_count': int,
            'channel_follower_count': int,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://piczel.tv/watch/DanishPenguin',
        'info_dict': {
            'id': '134312',
            'formats': list,
            'title': 'Chill with me while I draw!',
            'age_limit': int,
            'uploader': 'DanishPenguin',
            'uploader_id': 140134,
            'timestamp': 1772656712,
            'upload_date': '20260305',
            'ext': 'mp4',
            'description': "Welcome to my stream!\n\nThis is where I will be drawing SFW pieces and possible commissions if I should get them.\n\nBasic rules:\n\nUse **respectable** language! Don't swear too much please\n\nBe **nice** to each other in the chat! I assume we're all adults, so we should act as such.\n\nAnyone who acts up or does not follow these rules, will be blocked and banned from my streams. Don't take it personal if it happens, rules are rules. That and I also want to create a safe, cozy space while I stream 🙏\n\nThe first 3 who commissions me during my stream, will get a 30% discount on all tiers ✨ After that, the discount stops and normal prices will continue.\n\nIf you want to commission me, you can ask in the chat or even apply through this [Google Forms](https://tinyurl.com/yc4emkct)\n\nIt might be easier for me to send invoices and demand payment if you have applied through my Google Forms, so be aware of that!\n\nI will have LoFi running in the background as I draw, so if you don't want to hear it, you can just mute the stream.\n\nHope you enjoy the stream and my art! ❤\n\nHere are links to my socials:\n\n[Facebook](https://tinyurl.com/46aa66d4)\n\n[Instagram](https://tinyurl.com/296f59hh)\n\n[Twitter](https://tinyurl.com/56xpuh6y)\n\n[BlueSky](https://tinyurl.com/mrye9d8x)",
            'tags': list,
            'concurrent_view_count': int,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    def _extract_tags(self, stream) -> list:
        meta_tag = traverse_obj(stream, ('tags'), expected_type=list)
        if not meta_tag:
            return

        tag_list = []
        for tag in meta_tag:
            tag_list.append(tag.get('title'))
        return tag_list

    def _extract_formats(self, host, stream_id) -> list:
        return self._extract_m3u8_formats(f'https://boston.{host}/live/{stream_id}/llhls.m3u8', stream_id)

    def _get_user(self, data, user) -> dict:
        streams = traverse_obj(data, ('streams', 'streams'), expected_type=list)
        for i in range(len(streams)):
            tmp = traverse_obj(streams, (i, 'user'), expected_type=dict)
            if tmp.get('username') == user:
                return tmp
        return None

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        host = mobj.group('host') or 'piczel.tv'

        username = mobj.group('id')
        webpage = self._download_webpage(url, username)

        tmp = re.search(r'window.__PRELOADED_STATE__\s+=\s+(.*?)</script>', webpage).group(1)
        meta = json.loads(tmp)
        if not meta:
            raise ExtractorError(f'Could not find metadata for live stream: {url}')

        # multiple people can stream in the same room, all streams are found
        # in { 'streams': 'streams': [] } or in { 'entities': <username>: {} }
        main_stream = traverse_obj(meta, ('entities', 'streams', username), expected_type=dict)

        info = {
            'id': '',
            'title': None,
            'uploader': username,
            'uploader_id': int_or_none(self._get_user(meta, username).get('id')),
            'description': None,
            'tags': self._extract_tags(main_stream),
            'concurrent_view_count': int_or_none(main_stream.get('viewers')),
            'channel_follower_count': int_or_none(main_stream.get('follower_count')),
        }

        timestamp = unified_timestamp(main_stream.get('live_since')) or 0
        if timestamp:
            info['upload_date'] = datetime.datetime.fromtimestamp(timestamp=timestamp).strftime('%Y%m%d')
            info['timestamp'] = timestamp

        keymap = {
            'id': 'id',
            'title': 'title',
            'description': 'description',
        }

        for key in main_stream:
            if key in keymap:
                k = keymap[key]
                info[k] = main_stream[key]

        info['id'] = str(info['id'])
        info['formats'] = self._extract_formats(host, info['id'])

        formats = info['formats']
        for fmt in formats:
            if fmt.get('url') and re.search(r'video', fmt['url']):
                info['ext'] = fmt.get('ext')
                break

        info['age_limit'] = 18 if main_stream.get('adult') else 0

        return info
