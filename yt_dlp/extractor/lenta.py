from .common import InfoExtractor


class LentaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lenta\.ru/[^/]+/\d+/\d+/\d+/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://lenta.ru/news/2018/03/22/savshenko_go/',
        'info_dict': {
            'id': '964400',
            'ext': 'mp4',
            'title': 'Надежду Савченко задержали',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 61,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # EaglePlatform iframe embed
        'url': 'http://lenta.ru/news/2015/03/06/navalny/',
        'info_dict': {
            'id': '227304',
            'ext': 'mp4',
            'title': 'Навальный вышел на свободу',
            'description': 'md5:d97861ac9ae77377f3f20eaf9d04b4f5',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 87,
            'view_count': int,
            'age_limit': 0,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        video_id = self._search_regex(
            r'vid\s*:\s*["\']?(\d+)', webpage, 'eagleplatform id',
            default=None)
        if video_id:
            return self.url_result(
                'eagleplatform:lentaru.media.eagleplatform.com:%s' % video_id,
                ie='EaglePlatform', video_id=video_id)

        return self.url_result(url, ie='Generic')
