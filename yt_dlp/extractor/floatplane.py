import functools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    determine_ext,
    format_field,
    int_or_none,
    join_nonempty,
    parse_codecs,
    parse_iso8601,
    urljoin,
)
from ..utils.traversal import traverse_obj


class FloatplaneIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|beta)\.)?floatplane\.com/post/(?P<id>\w+)'
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
    }]

    def _real_initialize(self):
        if not self._get_cookies('https://www.floatplane.com').get('sails.sid'):
            self.raise_login_required()

    def _real_extract(self, url):
        post_id = self._match_id(url)

        post_data = self._download_json(
            'https://www.floatplane.com/api/v3/content/post', post_id, query={'id': post_id},
            note='Downloading post data', errnote='Unable to download post data')

        if not any(traverse_obj(post_data, ('metadata', ('hasVideo', 'hasAudio')))):
            raise ExtractorError('Post does not contain a video or audio track', expected=True)

        items = []
        for media in traverse_obj(post_data, (('videoAttachments', 'audioAttachments'), ...)):
            media_id = media['id']
            media_typ = media.get('type') or 'video'

            metadata = self._download_json(
                f'https://www.floatplane.com/api/v3/content/{media_typ}', media_id, query={'id': media_id},
                note=f'Downloading {media_typ} metadata')

            stream = self._download_json(
                'https://www.floatplane.com/api/v2/cdn/delivery', media_id, query={
                    'type': 'vod' if media_typ == 'video' else 'aod',
                    'guid': metadata['guid']
                }, note=f'Downloading {media_typ} stream data')

            path_template = traverse_obj(stream, ('resource', 'uri', {str}))

            def format_path(params):
                path = path_template
                for i, val in (params or {}).items():
                    path = path.replace(f'{{qualityLevelParams.{i}}}', val)
                return path

            formats = []
            for quality in traverse_obj(stream, ('resource', 'data', 'qualityLevels', ...)):
                url = urljoin(stream['cdn'], format_path(traverse_obj(
                    stream, ('resource', 'data', 'qualityLevelParams', quality['name']))))
                formats.append({
                    **traverse_obj(quality, {
                        'format_id': 'name',
                        'format_note': 'label',
                        'width': ('width', {int}),
                        'height': ('height', {int}),
                    }),
                    **parse_codecs(quality.get('codecs')),
                    'url': url,
                    'ext': determine_ext(url.partition('/chunk.m3u8')[0], 'mp4'),
                })

            items.append({
                'id': media_id,
                **traverse_obj(metadata, {
                    'title': 'title',
                    'duration': ('duration', {int_or_none}),
                    'thumbnail': ('thumbnail', 'path'),
                }),
                'formats': formats,
            })

        uploader_url = format_field(
            post_data, [('creator', 'urlname')], 'https://www.floatplane.com/channel/%s/home') or None
        channel_url = urljoin(f'{uploader_url}/', traverse_obj(post_data, ('channel', 'urlname')))

        post_info = {
            'id': post_id,
            'display_id': post_id,
            **traverse_obj(post_data, {
                'title': 'title',
                'description': ('text', {clean_html}),
                'uploader': ('creator', 'title'),
                'uploader_id': ('creator', 'id'),
                'channel': ('channel', 'title'),
                'channel_id': ('channel', 'id'),
                'like_count': ('likes', {int_or_none}),
                'dislike_count': ('dislikes', {int_or_none}),
                'comment_count': ('comments', {int_or_none}),
                'release_timestamp': ('releaseDate', {parse_iso8601}),
                'thumbnail': ('thumbnail', 'path'),
            }),
            'uploader_url': uploader_url,
            'channel_url': channel_url,
            'availability': self._availability(needs_subscription=True),
        }

        if len(items) > 1:
            return self.playlist_result(items, **post_info)

        post_info.update(items[0])
        return post_info


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
