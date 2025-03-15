from .common import InfoExtractor
from ..utils import ExtractorError


class JpFilmsIE(InfoExtractor):
    _VALID_URL = r'https?://jp-films\.com/watch-(?P<id>[^/]+)/.+html'
    _TESTS = [{
        'url': 'https://jp-films.com/watch-tokyo-trial/free-sv2.html',
        'md5': '219cc247503717c09fb65189ca4d7bda',
        'info_dict': {
            'id': 'tokyo-trial-8532',
            'ext': 'mp4',
            'title': 'Tokyo Trial',
            'age_limit': 0,
        },
    }]

    def _real_extract(self, url):
        url_slug = self._match_id(url)
        webpage = self._download_webpage(url, url_slug)
        video_data = self._search_json(
            r'.*var halim_cfg\s*=\s*', webpage, 'videoData', url_slug)

        if not video_data:
            raise ExtractorError('Video data not found', expected=True)

        nonce = self._search_regex(r'data-nonce=[\'"]([a-zA-Z0-9]+)[\'"]', webpage, 'nonce')
        post_id = str(video_data.get('post_id'))
        episode_slug = video_data.get('episode_slug')
        server = video_data.get('server')

        source_data = self._download_json(
            'https://jp-films.com/wp-content/themes/halimmovies/player.php',
            url_slug,
            query={
                'episode_slug': episode_slug,
                'server_id': server,
                'post_id': post_id,
                'nonce': nonce,
            },
            headers={
                'Referer': url,
                'X-Requested-With': 'XMLHttpRequest',
            },
        ).get('data')

        if not source_data:
            raise ExtractorError('Source data not found', expected=True)

        m3u8_url = self._search_regex(r'<source src=[\'"]([^"]+)[\'"]', source_data.get('sources'), 'source')

        return {
            'id': url_slug + '-' + post_id,
            'title': video_data.get('post_title')
            or self._html_search_regex(r'<span.*class=[\'"]last[\'"].*>(.+?)</span>', webpage, 'title'),
            'formats': self._extract_m3u8_formats(m3u8_url, url_slug, 'mp4', fatal=True),
            'age_limit': 18 if video_data.get('is_adult') else 0,
        }
