import functools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    determine_ext,
    float_or_none,
    format_field,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    url_or_none,
    urljoin,
)
from ..utils.traversal import require, traverse_obj


class FloatplaneBaseIE(InfoExtractor):
    def _real_extract(self, url):
        post_id = self._match_id(url)

        post_data = self._download_json(
            f'{self._BASE_URL}/api/v3/content/post', post_id, query={'id': post_id},
            note='Downloading post data', errnote='Unable to download post data',
            impersonate=self._IMPERSONATE_TARGET)

        if not any(traverse_obj(post_data, ('metadata', ('hasVideo', 'hasAudio')))):
            raise ExtractorError('Post does not contain a video or audio track', expected=True)

        uploader_url = format_field(
            post_data, [('creator', 'urlname')], f'{self._BASE_URL}/channel/%s/home') or None

        common_info = {
            'uploader_url': uploader_url,
            'channel_url': urljoin(f'{uploader_url}/', traverse_obj(post_data, ('channel', 'urlname'))),
            'availability': self._availability(needs_subscription=True),
            **traverse_obj(post_data, {
                'uploader': ('creator', 'title', {str}),
                'uploader_id': ('creator', 'id', {str}),
                'channel': ('channel', 'title', {str}),
                'channel_id': ('channel', 'id', {str}),
                'release_timestamp': ('releaseDate', {parse_iso8601}),
            }),
        }

        items = []
        for media in traverse_obj(post_data, (('videoAttachments', 'audioAttachments'), ...)):
            media_id = media['id']
            media_typ = media.get('type') or 'video'

            stream = self._download_json(
                f'{self._BASE_URL}/api/v3/delivery/info', media_id,
                query={'scenario': 'onDemand', 'entityId': media_id},
                note=f'Downloading {media_typ} stream data',
                impersonate=self._IMPERSONATE_TARGET)

            metadata = self._download_json(
                f'{self._BASE_URL}/api/v3/content/{media_typ}', media_id,
                f'Downloading {media_typ} metadata', query={'id': media_id},
                fatal=False, impersonate=self._IMPERSONATE_TARGET)

            cdn_base_url = traverse_obj(stream, (
                'groups', 0, 'origins', ..., 'url', {url_or_none}, any, {require('cdn base url')}))

            formats = []
            for variant in traverse_obj(stream, ('groups', 0, 'variants', lambda _, v: v['url'])):
                format_url = urljoin(cdn_base_url, variant['url'])
                format_id = traverse_obj(variant, ('name', {str}))
                hls_aes = {}
                m3u8_data = None

                # If we need impersonation for the API, then we need it for HLS keys too: extract in advance
                if self._IMPERSONATE_TARGET is not None:
                    m3u8_data = self._download_webpage(
                        format_url, media_id, fatal=False, impersonate=self._IMPERSONATE_TARGET, headers=self._HEADERS,
                        note=join_nonempty('Downloading', format_id, 'm3u8 information', delim=' '),
                        errnote=join_nonempty('Failed to download', format_id, 'm3u8 information', delim=' '))
                    if not m3u8_data:
                        continue

                    key_url = self._search_regex(
                        r'#EXT-X-KEY:METHOD=AES-128,URI="(https?://[^"]+)"',
                        m3u8_data, 'HLS AES key URI', default=None)
                    if key_url:
                        urlh = self._request_webpage(
                            key_url, media_id, fatal=False, impersonate=self._IMPERSONATE_TARGET, headers=self._HEADERS,
                            note=join_nonempty('Downloading', format_id, 'HLS AES key', delim=' '),
                            errnote=join_nonempty('Failed to download', format_id, 'HLS AES key', delim=' '))
                        if urlh:
                            hls_aes['key'] = urlh.read().hex()

                formats.append({
                    **traverse_obj(variant, {
                        'format_note': ('label', {str}),
                        'width': ('meta', 'video', 'width', {int_or_none}),
                        'height': ('meta', 'video', 'height', {int_or_none}),
                        'vcodec': ('meta', 'video', 'codec', {str}),
                        'acodec': ('meta', 'audio', 'codec', {str}),
                        'vbr': ('meta', 'video', 'bitrate', 'average', {int_or_none(scale=1000)}),
                        'abr': ('meta', 'audio', 'bitrate', 'average', {int_or_none(scale=1000)}),
                        'audio_channels': ('meta', 'audio', 'channelCount', {int_or_none}),
                        'fps': ('meta', 'video', 'fps', {float_or_none}),
                    }),
                    'url': format_url,
                    'ext': determine_ext(format_url.partition('/chunk.m3u8')[0], 'mp4'),
                    'format_id': format_id,
                    'hls_media_playlist_data': m3u8_data,
                    'hls_aes': hls_aes or None,
                })

            subtitles = {}
            automatic_captions = {}
            for sub_data in traverse_obj(metadata, ('textTracks', lambda _, v: url_or_none(v['src']))):
                sub_lang = sub_data.get('language') or 'en'
                sub_entry = {'url': sub_data['src']}
                if sub_data.get('generated'):
                    automatic_captions.setdefault(sub_lang, []).append(sub_entry)
                else:
                    subtitles.setdefault(sub_lang, []).append(sub_entry)

            items.append({
                **common_info,
                'id': media_id,
                **traverse_obj(metadata, {
                    'title': ('title', {str}),
                    'duration': ('duration', {int_or_none}),
                    'thumbnail': ('thumbnail', 'path', {url_or_none}),
                }),
                'formats': formats,
                'subtitles': subtitles,
                'automatic_captions': automatic_captions,
            })

        post_info = {
            **common_info,
            'id': post_id,
            'display_id': post_id,
            **traverse_obj(post_data, {
                'title': ('title', {str}),
                'description': ('text', {clean_html}),
                'like_count': ('likes', {int_or_none}),
                'dislike_count': ('dislikes', {int_or_none}),
                'comment_count': ('comments', {int_or_none}),
                'thumbnail': ('thumbnail', 'path', {url_or_none}),
            }),
            'http_headers': self._HEADERS,
        }

        if len(items) > 1:
            return self.playlist_result(items, **post_info)

        post_info.update(items[0])
        return post_info


class FloatplaneIE(FloatplaneBaseIE):
    _VALID_URL = r'https?://(?:(?:www|beta)\.)?floatplane\.com/post/(?P<id>\w+)'
    _BASE_URL = 'https://www.floatplane.com'
    _IMPERSONATE_TARGET = None
    _HEADERS = {
        'Origin': _BASE_URL,
        'Referer': f'{_BASE_URL}/',
    }
    _TESTS = [{
        'url': 'https://www.floatplane.com/post/2Yf3UedF7C',
        'info_dict': {
            'id': 'yuleLogLTT',
            'ext': 'mp4',
            'display_id': '2Yf3UedF7C',
            'title': '8K Yule Log Fireplace with Crackling Fire Sounds - 10 Hours',
            'description': 'md5:adf2970e0de1c5e3df447818bb0309f6',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'duration': 36035,
            'comment_count': int,
            'like_count': int,
            'dislike_count': int,
            'release_date': '20191206',
            'release_timestamp': 1575657000,
            'uploader': 'LinusTechTips',
            'uploader_id': '59f94c0bdd241b70349eb72b',
            'uploader_url': 'https://www.floatplane.com/channel/linustechtips/home',
            'channel': 'Linus Tech Tips',
            'channel_id': '63fe42c309e691e4e36de93d',
            'channel_url': 'https://www.floatplane.com/channel/linustechtips/home/main',
            'availability': 'subscriber_only',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.floatplane.com/post/j2jqG3JmgJ',
        'info_dict': {
            'id': 'j2jqG3JmgJ',
            'title': 'TJM: Does Anyone Care About Avatar: The Way of Water?',
            'description': 'md5:00bf17dc5733e4031e99b7fd6489f274',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'comment_count': int,
            'like_count': int,
            'dislike_count': int,
            'release_timestamp': 1671915900,
            'release_date': '20221224',
            'uploader': 'LinusTechTips',
            'uploader_id': '59f94c0bdd241b70349eb72b',
            'uploader_url': 'https://www.floatplane.com/channel/linustechtips/home',
            'channel': "They're Just Movies",
            'channel_id': '64135f82fc76ab7f9fbdc876',
            'channel_url': 'https://www.floatplane.com/channel/linustechtips/home/tajm',
            'availability': 'subscriber_only',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://www.floatplane.com/post/3tK2tInhoN',
        'info_dict': {
            'id': '3tK2tInhoN',
            'title': 'Extras - How Linus Communicates with Editors (Compensator 4)',
            'description': 'md5:83cd40aae1ce124df33769600c80ca5b',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'comment_count': int,
            'like_count': int,
            'dislike_count': int,
            'release_timestamp': 1700529120,
            'release_date': '20231121',
            'uploader': 'LinusTechTips',
            'uploader_id': '59f94c0bdd241b70349eb72b',
            'uploader_url': 'https://www.floatplane.com/channel/linustechtips/home',
            'channel': 'FP Exclusives',
            'channel_id': '6413623f5b12cca228a28e78',
            'channel_url': 'https://www.floatplane.com/channel/linustechtips/home/fpexclusive',
            'availability': 'subscriber_only',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://beta.floatplane.com/post/d870PEFXS1',
        'info_dict': {
            'id': 'bg9SuYKEww',
            'ext': 'mp4',
            'display_id': 'd870PEFXS1',
            'title': 'LCS Drama, TLOU 2 Remaster, Destiny 2 Player Count Drops, + More!',
            'description': 'md5:80d612dcabf41b17487afcbe303ec57d',
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'release_timestamp': 1700622000,
            'release_date': '20231122',
            'duration': 513,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'uploader': 'LinusTechTips',
            'uploader_id': '59f94c0bdd241b70349eb72b',
            'uploader_url': 'https://www.floatplane.com/channel/linustechtips/home',
            'channel': 'GameLinked',
            'channel_id': '649dbade3540dbc3945eeda7',
            'channel_url': 'https://www.floatplane.com/channel/linustechtips/home/gamelinked',
            'availability': 'subscriber_only',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.floatplane.com/post/65B5PNoBtf',
        'info_dict': {
            'id': '65B5PNoBtf',
            'description': 'I recorded the inbuilt demo mode for your 90\'s enjoyment, thanks for being Floaties!',
            'display_id': '65B5PNoBtf',
            'like_count': int,
            'release_timestamp': 1701249480,
            'uploader': 'The Trash Network',
            'availability': 'subscriber_only',
            'uploader_id': '61bc20c9a131fb692bf2a513',
            'uploader_url': 'https://www.floatplane.com/channel/TheTrashNetwork/home',
            'channel_url': 'https://www.floatplane.com/channel/TheTrashNetwork/home/thedrumthing',
            'comment_count': int,
            'title': 'The $50 electronic drum kit.',
            'channel_id': '64424fe73cd58cbcf8d8e131',
            'thumbnail': 'https://pbs.floatplane.com/blogPost_thumbnails/65B5PNoBtf/725555379422705_1701247052743.jpeg',
            'dislike_count': int,
            'channel': 'The Drum Thing',
            'release_date': '20231129',
        },
        'playlist_count': 2,
        'playlist': [{
            'info_dict': {
                'id': 'ISPJjexylS',
                'ext': 'mp4',
                'release_date': '20231129',
                'release_timestamp': 1701249480,
                'title': 'The $50 electronic drum kit. .mov',
                'channel_id': '64424fe73cd58cbcf8d8e131',
                'thumbnail': 'https://pbs.floatplane.com/video_thumbnails/ISPJjexylS/335202812134041_1701249383392.jpeg',
                'availability': 'subscriber_only',
                'uploader': 'The Trash Network',
                'duration': 622,
                'channel': 'The Drum Thing',
                'uploader_id': '61bc20c9a131fb692bf2a513',
                'channel_url': 'https://www.floatplane.com/channel/TheTrashNetwork/home/thedrumthing',
                'uploader_url': 'https://www.floatplane.com/channel/TheTrashNetwork/home',
            },
        }, {
            'info_dict': {
                'id': 'qKfxu6fEpu',
                'ext': 'aac',
                'release_date': '20231129',
                'release_timestamp': 1701249480,
                'title': 'Roland TD-7 Demo.m4a',
                'channel_id': '64424fe73cd58cbcf8d8e131',
                'availability': 'subscriber_only',
                'uploader': 'The Trash Network',
                'duration': 114,
                'channel': 'The Drum Thing',
                'uploader_id': '61bc20c9a131fb692bf2a513',
                'channel_url': 'https://www.floatplane.com/channel/TheTrashNetwork/home/thedrumthing',
                'uploader_url': 'https://www.floatplane.com/channel/TheTrashNetwork/home',
            },
        }],
        'skip': 'requires subscription: "The Trash Network"',
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_initialize(self):
        if not self._get_cookies(self._BASE_URL).get('sails.sid'):
            self.raise_login_required()


class FloatplaneChannelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|beta)\.)?floatplane\.com/channel/(?P<id>[\w-]+)/home(?:/(?P<channel>[\w-]+))?'
    _PAGE_SIZE = 20
    _TESTS = [{
        'url': 'https://www.floatplane.com/channel/linustechtips/home/ltxexpo',
        'info_dict': {
            'id': 'linustechtips/ltxexpo',
            'title': 'LTX Expo',
            'description': 'md5:9819002f9ebe7fd7c75a3a1d38a59149',
        },
        'playlist_mincount': 51,
    }, {
        'url': 'https://www.floatplane.com/channel/ShankMods/home',
        'info_dict': {
            'id': 'ShankMods',
            'title': 'Shank Mods',
            'description': 'md5:6dff1bb07cad8e5448e04daad9be1b30',
        },
        'playlist_mincount': 14,
    }, {
        'url': 'https://beta.floatplane.com/channel/bitwit_ultra/home',
        'info_dict': {
            'id': 'bitwit_ultra',
            'title': 'Bitwit Ultra',
            'description': 'md5:1452f280bb45962976d4789200f676dd',
        },
        'playlist_mincount': 200,
    }]

    def _fetch_page(self, display_id, creator_id, channel_id, page):
        query = {
            'id': creator_id,
            'limit': self._PAGE_SIZE,
            'fetchAfter': page * self._PAGE_SIZE,
        }
        if channel_id:
            query['channel'] = channel_id
        page_data = self._download_json(
            'https://www.floatplane.com/api/v3/content/creator', display_id,
            query=query, note=f'Downloading page {page + 1}')
        for post in page_data or []:
            yield self.url_result(
                f'https://www.floatplane.com/post/{post["id"]}',
                FloatplaneIE, id=post['id'], title=post.get('title'),
                release_timestamp=parse_iso8601(post.get('releaseDate')))

    def _real_extract(self, url):
        creator, channel = self._match_valid_url(url).group('id', 'channel')
        display_id = join_nonempty(creator, channel, delim='/')

        creator_data = self._download_json(
            'https://www.floatplane.com/api/v3/creator/named',
            display_id, query={'creatorURL[0]': creator})[0]

        channel_data = traverse_obj(
            creator_data, ('channels', lambda _, v: v['urlname'] == channel), get_all=False) or {}

        return self.playlist_result(OnDemandPagedList(functools.partial(
            self._fetch_page, display_id, creator_data['id'], channel_data.get('id')), self._PAGE_SIZE),
            display_id, title=channel_data.get('title') or creator_data.get('title'),
            description=channel_data.get('about') or creator_data.get('about'))
