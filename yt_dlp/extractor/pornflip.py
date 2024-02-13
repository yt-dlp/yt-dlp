from .common import InfoExtractor
from ..utils import int_or_none, parse_duration, parse_iso8601


class PornFlipIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pornflip\.com/(?:(embed|sv|v)/)?(?P<id>[^/]+)'
    _TESTS = [
        {
            'url': 'https://www.pornflip.com/dzv9Mtw1qj2/sv/brazzers-double-dare-two-couples-fucked-jenna-reid-maya-bijou',
            'info_dict': {
                'id': 'dzv9Mtw1qj2',
                'ext': 'mp4',
                'title': 'Brazzers - Double Dare Two couples fucked Jenna Reid Maya Bijou',
                'description': 'md5:d2b69e6cc743c5fd158e162aa7f05821',
                'duration': 476,
                'like_count': int,
                'dislike_count': int,
                'view_count': int,
                'timestamp': 1617846819,
                'upload_date': '20210408',
                'uploader': 'Brazzers',
                'age_limit': 18,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.pornflip.com/v/IrJEC40i21L',
            'only_matching': True,
        },
        {
            'url': 'https://www.pornflip.com/Z3jzbChC5-P/sexintaxi-e-sereyna-gomez-czech-naked-couple',
            'only_matching': True,
        },
        {
            'url': 'https://www.pornflip.com/embed/bLcDFxnrZnU',
            'only_matching': True,
        },
    ]
    _HOST = 'www.pornflip.com'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            'https://{}/sv/{}'.format(self._HOST, video_id), video_id, headers={'host': self._HOST})
        description = self._html_search_regex(r'&p\[summary\]=(.*?)\s*&p', webpage, 'description', fatal=False)
        duration = self._search_regex(r'"duration":\s+"([^"]+)",', webpage, 'duration', fatal=False)
        view_count = self._search_regex(r'"interactionCount":\s+"([^"]+)"', webpage, 'view_count', fatal=False)
        title = self._html_search_regex(r'id="mediaPlayerTitleLink"[^>]*>(.+)</a>', webpage, 'title', fatal=False)
        uploader = self._html_search_regex(r'class="title-chanel"[^>]*>[^<]*<a[^>]*>([^<]+)<', webpage, 'uploader', fatal=False)
        upload_date = self._search_regex(r'"uploadDate":\s+"([^"]+)",', webpage, 'upload_date', fatal=False)
        likes = self._html_search_regex(
            r'class="btn btn-up-rating[^>]*>[^<]*<i[^>]*>[^<]*</i>[^>]*<span[^>]*>[^0-9]*([0-9]+)[^<0-9]*<', webpage, 'like_count', fatal=False)
        dislikes = self._html_search_regex(
            r'class="btn btn-down-rating[^>]*>[^<]*<i[^>]*>[^<]*</i>[^>]*<span[^>]*>[^0-9]*([0-9]+)[^<0-9]*<', webpage, 'dislike_count', fatal=False)
        mpd_url = self._search_regex(r'"([^"]+userscontent.net/dash/[0-9]+/manifest.mpd[^"]*)"', webpage, 'mpd_url').replace('&amp;', '&')
        formats = self._extract_mpd_formats(mpd_url, video_id, mpd_id='dash')

        return {
            'age_limit': 18,
            'description': description,
            'dislike_count': int_or_none(dislikes),
            'duration': parse_duration(duration),
            'formats': formats,
            'id': video_id,
            'like_count': int_or_none(likes),
            'timestamp': parse_iso8601(upload_date),
            'thumbnail': self._og_search_thumbnail(webpage),
            'title': title,
            'uploader': uploader,
            'view_count': int_or_none(view_count),
        }
