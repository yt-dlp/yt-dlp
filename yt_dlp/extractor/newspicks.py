from .common import InfoExtractor
from ..utils import (
    clean_html,
    parse_iso8601,
    parse_qs,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class NewsPicksIE(InfoExtractor):
    _VALID_URL = r'https?://newspicks\.com/movie-series/(?P<id>[^?/#]+)'
    _TESTS = [{
        'url': 'https://newspicks.com/movie-series/11/?movieId=1813',
        'info_dict': {
            'id': '1813',
            'ext': 'mp4',
            'title': '日本の課題を破壊せよ【ゲスト：成田悠輔】',
            'cast': 'count:4',
            'description': 'md5:09397aad46d6ded6487ff13f138acadf',
            'release_date': '20220117',
            'release_timestamp': 1642424400,
            'series': 'HORIE ONE',
            'series_id': '11',
            'thumbnail': r're:https?://resources\.newspicks\.com/.+\.(?:jpe?g|png)',
            'timestamp': 1642424420,
            'upload_date': '20220117',
        },
    }, {
        'url': 'https://newspicks.com/movie-series/158/?movieId=3932',
        'info_dict': {
            'id': '3932',
            'ext': 'mp4',
            'title': '【検証】専門家は、KADOKAWAをどう見るか',
            'cast': 'count:3',
            'description': 'md5:2c2d4bf77484a4333ec995d676f9a91d',
            'release_date': '20240622',
            'release_timestamp': 1719088080,
            'series': 'NPレポート',
            'series_id': '158',
            'thumbnail': r're:https?://resources\.newspicks\.com/.+\.(?:jpe?g|png)',
            'timestamp': 1719086400,
            'upload_date': '20240622',
        },
    }]

    def _real_extract(self, url):
        series_id = self._match_id(url)
        video_id = traverse_obj(parse_qs(url), ('movieId', -1, {str}, {require('movie ID')}))
        webpage = self._download_webpage(url, video_id)

        fragment = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['fragment']
        m3u8_url = traverse_obj(fragment, ('movie', 'movieUrl', {url_or_none}, {require('m3u8 URL')}))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, 'mp4')

        return {
            'id': video_id,
            'formats': formats,
            'series': traverse_obj(fragment, ('series', 'title', {str})),
            'series_id': series_id,
            'subtitles': subtitles,
            **traverse_obj(fragment, ('movie', {
                'title': ('title', {str}),
                'cast': ('relatedUsers', ..., 'displayName', {str}, filter, all, filter),
                'description': ('explanation', {clean_html}),
                'release_timestamp': ('onAirStartDate', {parse_iso8601}),
                'thumbnail': (('image', 'coverImageUrl'), {url_or_none}, any),
                'timestamp': ('published', {parse_iso8601}),
            })),
        }
