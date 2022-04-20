from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    str_to_int,
    urlencode_postdata,
)


class ManyVidsIE(InfoExtractor):
    _VALID_URL = r'(?i)https?://(?:www\.)?manyvids\.com/video/(?P<id>\d+)'
    _TESTS = [{
        # preview video
        'url': 'https://www.manyvids.com/Video/133957/everthing-about-me/',
        'md5': '03f11bb21c52dd12a05be21a5c7dcc97',
        'info_dict': {
            'id': '133957',
            'ext': 'mp4',
            'title': 'everthing about me (Preview)',
            'view_count': int,
            'like_count': int,
        },
    }, {
        # full video
        'url': 'https://www.manyvids.com/Video/935718/MY-FACE-REVEAL/',
        'md5': 'f3e8f7086409e9b470e2643edb96bdcc',
        'info_dict': {
            'id': '935718',
            'ext': 'mp4',
            'title': 'MY FACE REVEAL',
            'view_count': int,
            'like_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_url = self._search_regex(
            r'data-(?:video-filepath|meta-video)\s*=s*(["\'])(?P<url>(?:(?!\1).)+)\1',
            webpage, 'video URL', group='url')

        title = self._html_search_regex(
            (r'<span[^>]+class=["\']item-title[^>]+>([^<]+)',
             r'<h2[^>]+class=["\']h2 m-0["\'][^>]*>([^<]+)'),
            webpage, 'title', default=None) or self._html_search_meta(
            'twitter:title', webpage, 'title', fatal=True)

        if any(p in webpage for p in ('preview_videos', '_preview.mp4')):
            title += ' (Preview)'

        mv_token = self._search_regex(
            r'data-mvtoken=(["\'])(?P<value>(?:(?!\1).)+)\1', webpage,
            'mv token', default=None, group='value')

        if mv_token:
            # Sets some cookies
            self._download_webpage(
                'https://www.manyvids.com/includes/ajax_repository/you_had_me_at_hello.php',
                video_id, fatal=False, data=urlencode_postdata({
                    'mvtoken': mv_token,
                    'vid': video_id,
                }), headers={
                    'Referer': url,
                    'X-Requested-With': 'XMLHttpRequest'
                })

        if determine_ext(video_url) == 'm3u8':
            formats = self._extract_m3u8_formats(
                video_url, video_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls')
        else:
            formats = [{'url': video_url}]

        like_count = int_or_none(self._search_regex(
            r'data-likes=["\'](\d+)', webpage, 'like count', default=None))
        view_count = str_to_int(self._html_search_regex(
            r'(?s)<span[^>]+class="views-wrapper"[^>]*>(.+?)</span', webpage,
            'view count', default=None))

        return {
            'id': video_id,
            'title': title,
            'view_count': view_count,
            'like_count': like_count,
            'formats': formats,
            'uploader': self._html_search_regex(r'<meta[^>]+name="author"[^>]*>([^<]+)', webpage, 'uploader'),
        }
