from .common import InfoExtractor


class PeekVidsIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?peekvids\.com/
        (?:(?:[^/?#]+/){2}|embed/?\?(?:[^#]*&)?v=)
        (?P<id>[^/?&#]*)
    '''
    _TESTS = [{
        'url': 'https://peekvids.com/pc/dane-jones-cute-redhead-with-perfect-tits-with-mini-vamp/BSyLMbN0YCd',
        'md5': 'a00940646c428e232407e3e62f0e8ef5',
        'info_dict': {
            'id': 'BSyLMbN0YCd',
            'title': ' Dane Jones - Cute redhead with perfect tits with Mini Vamp, SEXYhub',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'Watch  Dane Jones - Cute redhead with perfect tits with Mini Vamp (7 min), uploaded by SEXYhub.com',
            'timestamp': 1642579329,
            'upload_date': '20220119',
            'duration': 416,
            'view_count': int,
            'age_limit': 18,
        },
    }]
    _DOMAIN = 'www.peekvids.com'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        short_video_id = self._html_search_regex(r'<video [^>]*data-id="(.+?)"', webpage, 'short video ID')
        srcs = self._download_json(
            f'https://{self._DOMAIN}/v-alt/{short_video_id}', video_id,
            note='Downloading list of source files')
        formats = [{
            'url': url,
            'ext': 'mp4',
            'format_id': name[8:],
        } for name, url in srcs.items() if len(name) > 8 and name.startswith('data-src')]
        if not formats:
            formats = [{'url': url} for url in srcs.values()]

        info = self._search_json_ld(webpage, video_id, expected_type='VideoObject')
        info.update({
            'id': video_id,
            'age_limit': 18,
            'formats': formats,
        })
        return info


class PlayVidsIE(PeekVidsIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?://(?:www\.)?playvids\.com/(?:embed/|[^/]{2}/)?(?P<id>[^/?#]*)'
    _TESTS = [{
        'url': 'https://www.playvids.com/U3pBrYhsjXM/pc/dane-jones-cute-redhead-with-perfect-tits-with-mini-vamp',
        'md5': 'cd7dfd8a2e815a45402369c76e3c1825',
        'info_dict': {
            'id': 'U3pBrYhsjXM',
            'title': ' Dane Jones - Cute redhead with perfect tits with Mini Vamp, SEXYhub',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'Watch  Dane Jones - Cute redhead with perfect tits with Mini Vamp video in HD, uploaded by SEXYhub.com',
            'timestamp': 1640435839,
            'upload_date': '20211225',
            'duration': 416,
            'view_count': int,
            'age_limit': 18,
        },
    }, {
        'url': 'https://www.playvids.com/es/U3pBrYhsjXM/pc/dane-jones-cute-redhead-with-perfect-tits-with-mini-vamp',
        'only_matching': True,
    }, {
        'url': 'https://www.playvids.com/embed/U3pBrYhsjXM',
        'only_matching': True,
    }]
    _DOMAIN = 'www.playvids.com'
