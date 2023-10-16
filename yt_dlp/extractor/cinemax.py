from .hbo import HBOBaseIE


class CinemaxIE(HBOBaseIE):
    _VALID_URL = r'https?://(?:www\.)?cinemax\.com/(?P<path>[^/]+/video/[0-9a-z-]+-(?P<id>\d+))'
    _TESTS = [{
        'url': 'https://www.cinemax.com/warrior/video/s1-ep-1-recap-20126903',
        'md5': '82e0734bba8aa7ef526c9dd00cf35a05',
        'info_dict': {
            'id': '20126903',
            'ext': 'mp4',
            'title': 'S1 Ep 1: Recap',
        },
        'expected_warnings': ['Unknown MIME type application/mp4 in DASH manifest'],
    }, {
        'url': 'https://www.cinemax.com/warrior/video/s1-ep-1-recap-20126903.embed',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        path, video_id = self._match_valid_url(url).groups()
        info = self._extract_info('https://www.cinemax.com/%s.xml' % path, video_id)
        info['id'] = video_id
        return info
