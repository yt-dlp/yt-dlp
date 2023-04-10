import re

from .common import InfoExtractor


class HrefLiIE(InfoExtractor):
    _VALID_URL = r'https?://href\.li/\?(?P<url>.+)'

    _TESTS = [{
        'url': 'https://href.li/?https://www.reddit.com/r/cats/comments/12bluel/my_cat_helps_me_with_water/?utm_source=share&utm_medium=android_app&utm_name=androidcss&utm_term=1&utm_content=share_button',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(re.fullmatch(self._VALID_URL, url).group('url'))
