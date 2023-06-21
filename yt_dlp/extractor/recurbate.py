import urllib.error

from .common import InfoExtractor
from ..utils import ExtractorError, merge_dicts


class RecurbateIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?recurbate\.com/play\.php\?video=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://recurbate.com/play.php?video=39161415',
        'md5': 'dd2b4ec57aa3e3572cb5cf0997fca99f',
        'info_dict': {
            'id': '39161415',
            'ext': 'mp4',
            'description': 'md5:db48d09e4d93fc715f47fd3d6b7edd51',
            'title': 'Performer zsnicole33 show on 2022-10-25 20:23, Chaturbate Archive – Recurbate',
            'age_limit': 18,
        },
        'skip': 'Website require membership.',
    }]

    def _real_extract(self, url):
        SUBSCRIPTION_MISSING_MESSAGE = 'This video is only available for registered users; Set your authenticated browser user agent via the --user-agent parameter.'
        video_id = self._match_id(url)
        try:
            webpage = self._download_webpage(url, video_id)
        except ExtractorError as e:
            if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 403:
                self.raise_login_required(msg=SUBSCRIPTION_MISSING_MESSAGE, method='cookies')
            raise
        token = self._html_search_regex(r'data-token="([^"]+)"', webpage, 'token')
        video_url = f'https://recurbate.com/api/get.php?video={video_id}&token={token}'

        video_webpage = self._download_webpage(video_url, video_id)
        if video_webpage == 'shall_subscribe':
            self.raise_login_required(msg=SUBSCRIPTION_MISSING_MESSAGE, method='cookies')
        entries = self._parse_html5_media_entries(video_url, video_webpage, video_id)
        return merge_dicts({
            'id': video_id,
            'title': self._html_extract_title(webpage, 'title'),
            'description': self._og_search_description(webpage),
            'age_limit': self._rta_search(webpage),
        }, entries[0])
