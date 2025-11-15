import functools

from .common import InfoExtractor
from .floatplane import FloatplaneBaseIE
from ..utils import OnDemandPagedList, join_nonempty, parse_iso8601
from ..utils.traversal import traverse_obj


class SaucePlusIE(FloatplaneBaseIE):
    IE_DESC = 'Sauce+'
    _VALID_URL = r'https?://(?:(?:www|beta)\.)?sauceplus\.com/post/(?P<id>\w+)'
    _BASE_URL = 'https://www.sauceplus.com'
    _HEADERS = {
        'Origin': _BASE_URL,
        'Referer': f'{_BASE_URL}/',
    }
    _IMPERSONATE_TARGET = True
    _TESTS = [
        {
            'url': 'https://www.sauceplus.com/post/YbBwIa2A5g',
            'info_dict': {
                'id': 'eit4Ugu5TL',
                'ext': 'mp4',
                'display_id': 'YbBwIa2A5g',
                'title': 'Scare the Coyote - Episode 3',
                'description': '',
                'thumbnail': r're:^https?://.*\.jpe?g$',
                'duration': 2975,
                'comment_count': int,
                'like_count': int,
                'dislike_count': int,
                'release_date': '20250627',
                'release_timestamp': 1750993500,
                'uploader': 'Scare The Coyote',
                'uploader_id': '683e0a3269688656a5a49a44',
                'uploader_url': 'https://www.sauceplus.com/channel/ScareTheCoyote/home',
                'channel': 'Scare The Coyote',
                'channel_id': '683e0a326968866ceba49a45',
                'channel_url': 'https://www.sauceplus.com/channel/ScareTheCoyote/home/main',
                'availability': 'subscriber_only',
            },
            'params': {'skip_download': 'm3u8'},
        },
    ]

    def _real_initialize(self):
        if not self._get_cookies(self._BASE_URL).get('__Host-sp-sess'):
            self.raise_login_required()


class SaucePlusChannelIE(InfoExtractor):
    IE_DESC = 'Sauce+ channel'
    _VALID_URL = r'https?://(?:(?:www|beta)\.)?sauceplus\.com/channel/(?P<id>[\w-]+)/home(?:/(?P<channel>[\w-]+))?'
    _PAGE_SIZE = 20

    _TESTS = [
        {
            'url': 'https://www.sauceplus.com/channel/ScareTheCoyote/home',
            'info_dict': {
                'id': 'ScareTheCoyote',
                'title': 'Scare The Coyote',
            },
            'playlist_mincount': 7,
            'skip': 'requires subscription: Sauceplus',
        },
        {
            'url': 'https://www.sauceplus.com/channel/SafetyThird/home',
            'info_dict': {
                'id': 'SafetyThird',
                'title': 'Safety Third',
            },
            'playlist_mincount': 150,
            'skip': 'requires subscription: Sauceplus',
        },
    ]

    def _fetch_page(self, display_id, creator_id, channel_id, page):
        query = {
            'id': creator_id,
            'limit': self._PAGE_SIZE,
            'fetchAfter': page * self._PAGE_SIZE,
        }
        if channel_id:
            query['channel'] = channel_id
        page_data = self._download_json(
            'https://www.sauceplus.com/api/v3/content/creator',
            display_id,
            query=query,
            note=f'Downloading page {page + 1}',
        )
        for post in page_data or []:
            yield self.url_result(
                f"https://www.sauceplus.com/post/{post['id']}",
                SaucePlusIE,
                id=post['id'],
                title=post.get('title'),
                release_timestamp=parse_iso8601(post.get('releaseDate')),
            )

    def _real_extract(self, url):
        creator, channel = self._match_valid_url(url).group('id', 'channel')
        display_id = join_nonempty(creator, channel, delim='/')

        creator_data = self._download_json(
            'https://www.sauceplus.com/api/v3/creator/named',
            display_id,
            query={'creatorURL[0]': creator},
        )[0]

        channel_data = (
            traverse_obj(creator_data, ('channels', lambda _, v: v['urlname'] == channel), get_all=False) or {}
        )

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(self._fetch_page, display_id, creator_data['id'], channel_data.get('id')),
                self._PAGE_SIZE,
            ),
            display_id,
            title=channel_data.get('title') or creator_data.get('title'),
            description=channel_data.get('about') or creator_data.get('about'),
        )
