import urllib.parse

from .common import InfoExtractor
from ..utils import parse_duration, remove_end, unified_strdate, urljoin


class NDTVIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:[^/]+\.)?ndtv\.com/(?:[^/]+/)*videos?/?(?:[^/]+/)*[^/?^&]+-(?P<id>\d+)'

    _TESTS = [
        {
            'url': 'https://khabar.ndtv.com/video/show/prime-time/prime-time-ill-system-and-poor-education-468818',
            'md5': '78efcf3880ef3fd9b83d405ca94a38eb',
            'info_dict': {
                'id': '468818',
                'ext': 'mp4',
                'title': 'प्राइम टाइम: सिस्टम बीमार, स्कूल बदहाल',
                'description': 'md5:f410512f1b49672e5695dea16ef2731d',
                'upload_date': '20170928',
                'duration': 2218,
                'thumbnail': r're:https?://.*\.jpg',
            },
        },
        {
            # __filename is url
            'url': 'http://movies.ndtv.com/videos/cracker-free-diwali-wishes-from-karan-johar-kriti-sanon-other-stars-470304',
            'md5': 'f1d709352305b44443515ac56b45aa46',
            'info_dict': {
                'id': '470304',
                'ext': 'mp4',
                'title': 'Cracker-Free Diwali Wishes From Karan Johar, Kriti Sanon & Other Stars',
                'description': 'md5:f115bba1adf2f6433fa7c1ade5feb465',
                'upload_date': '20171019',
                'duration': 137,
                'thumbnail': r're:https?://.*\.jpg',
            },
        },
        {
            'url': 'https://www.ndtv.com/video/news/news/delhi-s-air-quality-status-report-after-diwali-is-very-poor-470372',
            'only_matching': True,
        },
        {
            'url': 'https://auto.ndtv.com/videos/the-cnb-daily-october-13-2017-469935',
            'only_matching': True,
        },
        {
            'url': 'https://sports.ndtv.com/cricket/videos/2nd-t20i-rock-thrown-at-australia-cricket-team-bus-after-win-over-india-469764',
            'only_matching': True,
        },
        {
            'url': 'http://gadgets.ndtv.com/videos/uncharted-the-lost-legacy-review-465568',
            'only_matching': True,
        },
        {
            'url': 'http://profit.ndtv.com/videos/news/video-indian-economy-on-very-solid-track-international-monetary-fund-chief-470040',
            'only_matching': True,
        },
        {
            'url': 'http://food.ndtv.com/video-basil-seeds-coconut-porridge-419083',
            'only_matching': True,
        },
        {
            'url': 'https://doctor.ndtv.com/videos/top-health-stories-of-the-week-467396',
            'only_matching': True,
        },
        {
            'url': 'https://swirlster.ndtv.com/video/how-to-make-friends-at-work-469324',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # '__title' does not contain extra words such as sub-site name, "Video" etc.
        title = urllib.parse.unquote_plus(
            self._search_regex(r"__title\s*=\s*'([^']+)'", webpage, 'title', default=None)
            or self._og_search_title(webpage))

        filename = self._search_regex(
            r"(?:__)?filename\s*[:=]\s*'([^']+)'", webpage, 'video filename')
        # in "movies" sub-site pages, filename is URL
        video_url = urljoin('https://ndtvod.bc-ssl.cdn.bitgravity.com/23372/ndtv/', filename.lstrip('/'))

        # "doctor" sub-site has MM:SS format
        duration = parse_duration(self._search_regex(
            r"(?:__)?duration\s*[:=]\s*'([^']+)'", webpage, 'duration', fatal=False))

        # "sports", "doctor", "swirlster" sub-sites don't have 'publish-date'
        upload_date = unified_strdate(self._html_search_meta(
            'publish-date', webpage, 'upload date', default=None) or self._html_search_meta(
            'uploadDate', webpage, 'upload date', default=None) or self._search_regex(
            r'datePublished"\s*:\s*"([^"]+)"', webpage, 'upload date', fatal=False))

        description = remove_end(self._og_search_description(webpage), ' (Read more)')

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': self._og_search_thumbnail(webpage),
            'duration': duration,
            'upload_date': upload_date,
        }
