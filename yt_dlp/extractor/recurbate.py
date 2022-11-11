from .common import InfoExtractor
from ..utils import ExtractorError, merge_dicts


class RecurbateIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?recurbate\.com/play\.php\?video=(?P<id>[0-9]+)'
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
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._html_extract_title(webpage, 'title')
        token = self._html_search_regex(r'data-token="([^"]+)"', webpage, 'token')

        video_url = f'https://recurbate.com/api/get.php?video={video_id}&token={token}'
        video_webpage = self._download_webpage(video_url, video_id)
        if 'shall_signin' in video_webpage[:20]:
            self.raise_login_required(method='cookies')

        entries = self._parse_html5_media_entries(video_url, video_webpage, video_id)
        if not entries:
            raise ExtractorError('No media links found')
        return merge_dicts({
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'age_limit': self._rta_search(webpage),
        }, entries[0])
