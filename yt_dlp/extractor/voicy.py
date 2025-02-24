import calendar
import itertools
import time
import urllib.parse

from .wrestleuniverse import WrestleUniverseBaseIE
from ..utils import (
    ExtractorError,
    float_or_none,
    merge_dicts,
    parse_iso8601,
    parse_qs,
    str_or_none,
    update_url,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class VoicyBaseIE(WrestleUniverseBaseIE):
    _LOGIN_HEADERS = {
        'Content-Type': 'application/json',
        'X-Client-Version': 'Chrome/JsCore/10.13.2/FirebaseCore-web',
        'X-Firebase-Gmpid': '1:212371279501:web:318567ddcbb953adcc5cc4',
    }
    _LOGIN_HINT = (
        'Use --username refresh --password <refreshToken>, --username and --password, '
        '--netrc-cmd, or --netrc (voicy) to provide account credentials')
    _LOGIN_QUERY = {'key': 'AIzaSyC5Rg-sxiYu6ySD8V-f6Eljwll8gHvgUK4'}
    _NETRC_MACHINE = 'voicy'

    @WrestleUniverseBaseIE._TOKEN.getter
    def _TOKEN(self):
        if not self._REAL_TOKEN or self._TOKEN_EXPIRY <= int(time.time()):
            if not self._REFRESH_TOKEN:
                self.raise_login_required(
                    f'No refreshToken provided. {self._LOGIN_HINT}', method=None)
            self._refresh_token()
        return self._REAL_TOKEN

    def _perform_login(self, username, password):
        if username.lower() == 'refresh':
            self._REFRESH_TOKEN = password
            return self._refresh_token()
        return super()._perform_login(username, password)

    def _call_api(self, path, some_id, note='Downloading JSON metadata', headers=None, query=None, fatal=True):
        return self._download_json(
            f'https://vmedia-player-api.voicy.jp/v1/{path}', some_id, note=note, headers={
                'Authorization': f'Bearer {self._TOKEN}',
            } | (headers or {}), query=query, fatal=fatal,
        )


class VoicyIE(VoicyBaseIE):
    IE_NAME = 'voicy'
    IE_DESC = 'Voicy'

    _VALID_URL = [
        r'https?://(?:www\.)?voicy\.jp/channel/(?P<channel>\d+)/(?P<id>\d+)',
        r'http://r\.voicy\.jp/\w+',
    ]
    _TESTS = [{
        'url': 'https://voicy.jp/channel/3402/6361249',
        'info_dict': {
            'id': '8576738',
            'ext': 'm4a',
            'title': '2025.1.19「ブラジル沖の白石康次郎さん＆息子の成人式を『1年』間違えたお母さん」',
            'categories': ['トーク', '声優・アナウンサー'],
            'channel': '安住紳一郎の日曜天国',
            'channel_id': '3402',
            'comment_count': int,
            'description': 'md5:f39bb238ff7661c3b7e8934f8578cf33',
            'display_id': '6361249',
            'duration': 1588.741,
            'like_count': int,
            'release_date': '20250119',
            'release_timestamp': 1737272164,
            'series': '2025.1.19「ブラジル沖の白石康次郎さん＆息子の成人式を『1年』間違えたお母さん」',
            'series_id': '6361249',
            'thumbnail': r're:https://files\.voicy\.jp/img/speaker/.+$',
            'uploader': 'TBS RADIO',
            'uploader_id': '17328',
            'view_count': int,
        },
    }, {
        'url': 'https://voicy.jp/channel/3272/1141448',
        'info_dict': {
            'id': '2757390',
            'ext': 'mp3',
            'title': '5/3 お久しぶり雑談回',
            'categories': ['トーク', '声優・アナウンサー'],
            'channel': '松嵜麗のボイログ！',
            'channel_id': '3272',
            'comment_count': int,
            'description': 'md5:4dee911d23cf1eedeb49687881878119',
            'display_id': '1141448',
            'duration': 433.24,
            'like_count': int,
            'release_date': '20240502',
            'release_timestamp': 1714662728,
            'series': '最近のわたし',
            'series_id': '1141448',
            'tags': ['最近のマイブーム'],
            'thumbnail': r're:https://files\.voicy\.jp/img/speaker/.+$',
            'uploader': '声優・松嵜麗',
            'uploader_id': '16462',
            'view_count': int,
        },
    }, {
        'url': 'https://voicy.jp/channel/1417/6436213',
        'info_dict': {
            'id': '6436213',
            'title': '第100回 グリム兄弟「麦のほ」',
        },
        'playlist_count': 5,
        'skip': 'Only available for premium supporters',
    }, {
        'url': 'http://r.voicy.jp/7Qm2JbexmY6',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        if not url.startswith('https'):
            return self.url_result(update_url(url, scheme='https'))

        channel_id, audio_id = self._match_valid_url(url).groups()
        channel_info = {
            'channel_id': channel_id,
            **traverse_obj(self._call_api(f'channel/{channel_id}', channel_id), {
                'categories': ('category', ('name', ('subcategory', 'name'), {str})),
                'channel': ('name', {str}),
                'thumbnail': ('image', {url_or_none}),
                'uploader': ('personality', 'name', {str}),
                'uploader_id': ('personality', 'id', {str_or_none}),
            }),
        }

        audio_info = self._call_api(f'channels/{channel_id}/stories/{audio_id}', audio_id)
        common_info = {
            'description': self._call_api(
                f'channels/{channel_id}/stories/{audio_id}/description', audio_id, fatal=False,
            ).get('description'),
            'display_id': audio_id,
            'series': audio_info['name'],
            'series_id': audio_id,
            **traverse_obj(audio_info, {
                'comment_count': ('comment_count', {int}),
                'like_count': ('like_count', {int}),
                'release_timestamp': ('published', {parse_iso8601}),
                'tags': ('hashtags', ..., 'name', {str}),
            }),
        }

        all_entries = traverse_obj(audio_info, ('chapters', ..., {
            'id': ('id', {str_or_none}),
            'title': ('name', {str}),
            'duration': ('voice', 'duration', {float_or_none(scale=1000)}),
            'manifest': ('voice', 'file', {url_or_none}),
            'view_count': ('play_count', {int}),
        }))

        entries = []
        for entry in all_entries:
            if manifest := entry.pop('manifest', None):
                ext = 'm4a' if 'audio_hls_aac' in manifest else 'mp3'
                merged = merge_dicts(entry, channel_info, common_info, {
                    'formats': self._extract_m3u8_formats(manifest, audio_id, ext),
                })
                if len(all_entries) == 1:
                    return merged
                entries.append(merged)
        if not entries:
            self.raise_login_required(
                f'Premium(VIP) authentication required. {self._LOGIN_HINT}', method=None)

        return self.playlist_result(entries, audio_id, audio_info['name'])


class VoicyLiveIE(VoicyBaseIE):
    IE_NAME = 'voicy:live'

    _VALID_URL = r'https?://(?:www\.)?voicy\.jp/channel/\d+/live/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://voicy.jp/channel/1417/live/4858078',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        live_info = self._call_api(
            f'live/{audio_id}', audio_id, headers={'X-Platform': '3'})
        if live_info['status'] != 'ended':
            raise ExtractorError('WebRTC is not currently supported', expected=True)
        if share_url := traverse_obj(live_info, ('archive', 'share_url', {url_or_none})):
            return self.url_result(share_url, VoicyIE)
        self.raise_no_formats(
            'This livestream has ended and no archive is available', expected=True)


class VoicyPlaylistBaseIE(VoicyBaseIE):
    def _entries(self, path, some_id, query, keys, ie=VoicyIE):
        pagination = ''

        for page in itertools.count(1):
            info = self._call_api(
                path, some_id, f'Downloading page {page}',
                query={
                    'page_size': '100',
                    'page_token': pagination,
                } | (query or {}),
            )
            yield from (self.url_result(s, ie) for s in traverse_obj(info, (*keys, 'share_url', {url_or_none})))

            if not (pagination := traverse_obj(info, ('pagination', 'next_page_token', {str}))):
                break
            self._sleep(1, some_id)


class VoicyChannelIE(VoicyPlaylistBaseIE):
    IE_NAME = 'voicy:channel'

    _VALID_URL = r'https?://(?:www\.)?voicy\.jp/channel/(?P<id>\d+)(?:/(?P<type>all|backnumber/\d+|premium))?(?:\?|$)'
    _TESTS = [{
        'url': 'https://voicy.jp/channel/3402',
        'info_dict': {
            'id': '3402',
            'title': '安住紳一郎の日曜天国',
        },
        'playlist_mincount': 107,
    }, {
        'url': 'https://voicy.jp/channel/1/premium',
        'info_dict': {
            'id': '1',
            'title': 'Voicy社長の頭の中',
        },
        'playlist_mincount': 145,
    }, {
        'url': 'https://voicy.jp/channel/2856/all',
        'info_dict': {
            'id': '2856',
            'title': 'そんなこんなで、茅原実里です',
        },
        'playlist_mincount': 62,
    }, {
        'url': 'https://voicy.jp/channel/3321/all?type=all&month=202412',
        'info_dict': {
            'id': '3321',
            'title': '海外安全チャンネル・りょーあん',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://voicy.jp/channel/1417/backnumber/202501',
        'info_dict': {
            'id': '1417',
            'title': '繪ほんの中には 公式チャンネル',
        },
        'playlist_count': 5,
    }]

    def _real_extract(self, url):
        channel_id, _type = self._match_valid_url(url).groups()
        channel_info = self._call_api(f'channel/{channel_id}', channel_id)
        query = {
            'filter_type' if k == 'type' else k: v[0]
            for k, v in parse_qs(url).items() if v
        } | {'channel_view_id': channel_id, 'order': 'new'}

        if _type == 'premium':
            query['filter_type'] = 'premium'
        elif (ym := query.pop('month', None) or (_type not in ('all', None) and _type.split('/')[-1])):
            y, m = map(int, (ym[:4], ym[4:]))
            d = calendar.monthrange(y, m)[1]
            query.update({
                'from': f'{y}-{m:02d}-01T00:00:00+09:00',
                'to': f'{y}-{m:02d}-{d}T23:59:59+09:00',
            })

        return self.playlist_result(self._entries(
            'stories', channel_id, query, ('stories', ...),
        ), channel_id, channel_info['name'])


class VoicyTopicIE(VoicyPlaylistBaseIE):
    IE_NAME = 'voicy:topic'

    _VALID_URL = r'https?://(?:www\.)?voicy\.jp/(?P<id>{})(?:/(?P<ctg_or_kwd>[\w%]+))?(?:/(?P<sub_ctg>[\w-]+))?'.format(
        '|'.join(('audiobook', 'category', 'follow(?:ing-paystory)?', 'hashtag', 'paystory', 'pickup', 'search', 'voicedrama')))
    _TESTS = [{
        'url': 'https://voicy.jp/audiobook',
        'info_dict': {
            'id': '111',
            'title': 'audiobook',
        },
        'playlist_mincount': 96,
    }, {
        'url': 'https://voicy.jp/category/talk/voiceactor-announcer',
        'info_dict': {
            'id': 'voiceactor-announcer',
            'title': '声優・アナウンサー',
        },
        'playlist_mincount': 70,
    }, {
        'url': 'https://voicy.jp/category/sports/all',
        'info_dict': {
            'id': 'sports',
            'title': 'スポーツ',
        },
        'playlist_mincount': 174,
    }, {
        'url': 'https://voicy.jp/hashtag/%E3%82%B9%E3%83%9E%E3%83%BC%E3%83%88%E5%AE%B6%E9%9B%BB',
        'info_dict': {
            'id': 'hashtag',
            'title': 'スマート家電',
        },
        'playlist_mincount': 14,
    }, {
        'url': 'https://voicy.jp/search/%E6%81%B5%E6%96%B9%E5%B7%BB%E3%81%8D',
        'info_dict': {
            'id': 'search',
            'title': '恵方巻き',
        },
        'playlist_mincount': 102,
    }, {
        'url': 'https://voicy.jp/follow',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        topic = self._match_id(url)
        topic_id, is_story, ie = {
            'audiobook': ('111', False, VoicyChannelIE),
            'category': ('category', False, VoicyChannelIE),
            'follow': ('1', True, VoicyIE),
            'following-paystory': ('94', True, VoicyIE),
            'hashtag': ('hashtag', True, VoicyIE),
            'paystory': ('70', True, VoicyIE),
            'pickup': ('21', False, VoicyChannelIE),
            'search': ('search', True, VoicyIE),
            'voicedrama': ('93', False, VoicyChannelIE),
        }[topic]

        keys = ('channels', ..., *('story',) * is_story)
        if topic == 'category':
            ctg, sub_ctg = self._match_valid_url(url).group('ctg_or_kwd', 'sub_ctg')
            category = topic_id = sub_ctg if (has_sub := sub_ctg != 'all') else ctg
            category_id, topic = traverse_obj(self._call_api('channel/categories', None), (
                *((..., 'subcategories') if has_sub else ()),
                lambda _, v: v['view_id'] == category, ('id', 'name'), {str_or_none},
            ))
            path = f'channel/categories/{category_id}'
            query = {'exclude_story': 'true'}
        elif topic in ('hashtag', 'search'):
            keyword = self._match_valid_url(urllib.parse.unquote(url)).group('ctg_or_kwd')
            if not keyword:
                raise ExtractorError('Invalid URL', expected=True)
            path = 'search/channels/story'
            query = {
                'search_type': {
                    'hashtag': 'hashtag',
                    'search': 'words',
                }[topic],
                'words': keyword,
            }
            topic = keyword
        elif topic_id == '1':
            path = 'user/me/channels/story/following'
            query = {'series_filter': '2'}
        else:
            path = f'topics/channels{"/story" * is_story}'
            query = {'topic_id': topic_id}
            keys = (..., *keys)

        return self.playlist_result(self._entries(path, topic_id, query, keys, ie), topic_id, topic)
