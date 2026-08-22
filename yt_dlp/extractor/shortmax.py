from .common import InfoExtractor
from ..utils import update_url


class ShortMaxIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?:www\.)?shorttv\.live/(?:(?:[^/]+)/)?episode/.+?-(?P<id>\d+)-\d+/?$'
    )
    _TESTS = [{
        'url': 'https://www.shorttv.live/episode/no-more-promises-wed-to-the-general-27901-1',
        'md5': 'f3832b6279b9578c78047ddf974bc747',
        'info_dict': {
            'id': 'no-more-promises-wed-to-the-general-27901-1',
            'ext': 'mp4',
            'thumbnail': 'https://akamai-static.shorttv.live/images/cover/2026/07/15/7ad441f0e2524001a1d753e16446c8b8.jpg',
            'title': 'No More Promises: Wed to the General - Episode 1 - ShortMax',
        },
    },
        {
        'url': 'https://www.shorttv.live/episode/no-more-promises-wed-to-the-general-27901-2',
        'md5': '0f834dfb5d0fd27cb1c67868798f9277',
        'info_dict': {
            'id': 'no-more-promises-wed-to-the-general-27901-2',
            'ext': 'mp4',
            'thumbnail': 'https://akamai-static.shorttv.live/images/cover/2026/07/15/92f7a53b866b4227b079f699db9e3054.jpg',
            'title': 'No More Promises: Wed to the General - Episode 2 - ShortMax',
        },
    },
        {
        'url': 'https://www.shorttv.live/ja/episode/潜入バトル令嬢はスパ派遣-7002-1',
        'md5': '6da8855456f11d6f979eb6de21c497c2',
        'info_dict': {
            'id': '潜入バトル令嬢はスパ派遣-7002-1',
            'ext': 'mp4',
            'thumbnail': 'https://akamai-static.shorttv.live/images/cover/2025/05/12/20702ab59f0940048505dbe368ddab8a.jpg',
            'title': '潜入バトル！令嬢はスーパー派遣 - 第1話 - ShortMax',
        },
    }]

    def _real_extract(self, url):
        video_id = self._generic_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_extract_title(webpage)
        thumbnail_url = update_url(self._html_search_meta('og:image', webpage), query='')

        nuxt_json = self._search_nuxt_json(webpage, video_id)
        episodes = nuxt_json['data'][[*nuxt_json['_errors'].keys()][-1]]['data']['episodeList']

        N = 0
        for i in range(len(episodes)):
            if episodes[i]['frameExtractionCover'] == thumbnail_url:
                N = i
                break

        vid_formats = self._parse_json(episodes[N]['encryptedVideoUrl'], video_id)
        formats = [self._extract_m3u8_formats(vid_formats['video_480'], video_id, 'mp4', m3u8_id='hls')[0],
                   self._extract_m3u8_formats(vid_formats['video_720'], video_id, 'mp4', m3u8_id='hls')[0],
                   self._extract_m3u8_formats(vid_formats['video_1080'], video_id, 'mp4', m3u8_id='hls')[0]]

        for fmt in formats:
            fmt['protocol'] = 'm3u8_shortmax'

        return {
            'id': video_id,
            'ext': 'mp4',
            'formats': formats,
            'thumbnail': thumbnail_url,
            'title': title,
        }
