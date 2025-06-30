from .floatplane import FloatplaneBaseIE


class SaucePlusIE(FloatplaneBaseIE):
    IE_DESC = 'Sauce+'
    _VALID_URL = r'https?://(?:(?:www|beta)\.)?sauceplus\.com/post/(?P<id>\w+)'
    _BASE_URL = 'https://www.sauceplus.com'
    _HEADERS = {
        'Origin': _BASE_URL,
        'Referer': f'{_BASE_URL}/',
    }
    _IMPERSONATE_TARGET = True
    _TESTS = [{
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
    }]

    def _real_initialize(self):
        if not self._get_cookies(self._BASE_URL).get('__Host-sp-sess'):
            self.raise_login_required()
