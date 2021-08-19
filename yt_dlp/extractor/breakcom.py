from __future__ import unicode_literals


from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    int_or_none,
    url_or_none,
)


class BreakIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?break\.com/video/(?P<display_id>[^/]+?)(?:-(?P<id>\d+))?(?:[/?#&]|$)'
    _TESTS = [{
        'url': 'http://www.break.com/video/when-girls-act-like-guys-2468056',
        'info_dict': {
            'id': '2468056',
            'ext': 'mp4',
            'title': 'When Girls Act Like D-Bags',
            'age_limit': 13,
        },
    }, {
        # youtube embed
        'url': 'http://www.break.com/video/someone-forgot-boat-brakes-work',
        'info_dict': {
            'id': 'RrrDLdeL2HQ',
            'ext': 'mp4',
            'title': 'Whale Watching Boat Crashing Into San Diego Dock',
            'description': 'md5:afc1b2772f0a8468be51dd80eb021069',
            'upload_date': '20160331',
            'uploader': 'Steve Holden',
            'uploader_id': 'sdholden07',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'http://www.break.com/video/ugc/baby-flex-2773063',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).groups()

        webpage = self._download_webpage(url, display_id)

        youtube_url = YoutubeIE._extract_url(webpage)
        if youtube_url:
            return self.url_result(youtube_url, ie=YoutubeIE.ie_key())

        content = self._parse_json(
            self._search_regex(
                r'(?s)content["\']\s*:\s*(\[.+?\])\s*[,\n]', webpage,
                'content'),
            display_id)

        formats = []
        for video in content:
            video_url = url_or_none(video.get('url'))
            if not video_url:
                continue
            bitrate = int_or_none(self._search_regex(
                r'(\d+)_kbps', video_url, 'tbr', default=None))
            formats.append({
                'url': video_url,
                'format_id': 'http-%d' % bitrate if bitrate else 'http',
                'tbr': bitrate,
            })
        self._sort_formats(formats)

        title = self._search_regex(
            (r'title["\']\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
             r'<h1[^>]*>(?P<value>[^<]+)'), webpage, 'title', group='value')

        def get(key, name):
            return int_or_none(self._search_regex(
                r'%s["\']\s*:\s*["\'](\d+)' % key, webpage, name,
                default=None))

        age_limit = get('ratings', 'age limit')
        video_id = video_id or get('pid', 'video id') or display_id

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'thumbnail': self._og_search_thumbnail(webpage),
            'age_limit': age_limit,
            'formats': formats,
        }
