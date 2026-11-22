from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import (
    ExtractorError,
    join_nonempty,
)
from ..utils.traversal import traverse_obj


class CroatianFilmIE(InfoExtractor):
    IE_NAME = 'croatian.film'
    _VALID_URL = r'https://?(?:www\.)?croatian\.film/[a-z]{2}/[^/?#]+/(?P<id>\d+)'
    _GEO_COUNTRIES = ['HR']

    _TESTS = [{
        'url': 'https://www.croatian.film/hr/films/72472',
        'info_dict': {
            'id': '1078340774',
            'ext': 'mp4',
            'title': '“ŠKAFETIN”, r. Paško Vukasović',
            'uploader': 'croatian.film',
            'uploader_id': 'user94192658',
            'uploader_url': 'https://vimeo.com/user94192658',
            'duration': 1357,
            'thumbnail': 'https://i.vimeocdn.com/video/2008556407-40eb1315ec11be5fcb8dda4d7059675b0881e182b9fc730892e267db72cb57f5-d',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to parse XML: not well-formed'],
    }, {
        # geo-restricted but works with xff
        'url': 'https://www.croatian.film/en/films/77144',
        'info_dict': {
            'id': '1144997795',
            'ext': 'mp4',
            'title': '“ROKO” r. Ivana Marinić Kragić',
            'uploader': 'croatian.film',
            'uploader_id': 'user94192658',
            'uploader_url': 'https://vimeo.com/user94192658',
            'duration': 1023,
            'thumbnail': 'https://i.vimeocdn.com/video/2093793231-11c2928698ff8347489e679b4d563a576e7acd0681ce95b383a9a25f6adb5e8f-d',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to parse XML: not well-formed'],
    }, {
        'url': 'https://www.croatian.film/en/films/75904/watch',
        'info_dict': {
            'id': '1134883757',
            'ext': 'mp4',
            'title': '"CARPE DIEM" r. Nina Damjanović',
            'uploader': 'croatian.film',
            'uploader_id': 'user94192658',
            'uploader_url': 'https://vimeo.com/user94192658',
            'duration': 1123,
            'thumbnail': 'https://i.vimeocdn.com/video/2080022187-bb691c470c28c4d979258cf235e594bf9a11c14b837a0784326c25c95edd83f9-d',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to parse XML: not well-formed'],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        api_data = self._download_json(
            f'https://api.croatian.film/api/videos/{display_id}',
            display_id)

        if errors := traverse_obj(api_data, ('errors', lambda _, v: v['code'])):
            codes = traverse_obj(errors, (..., 'code', {str}))
            if 'INVALID_COUNTRY' in codes:
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            raise ExtractorError(join_nonempty(
                *(traverse_obj(errors, (..., 'details', {str})) or codes),
                delim='; '))

        vimeo_id = self._search_regex(
            r'/videos/(\d+)', api_data['video']['vimeoURL'], 'vimeo ID')

        return self.url_result(
            VimeoIE._smuggle_referrer(f'https://player.vimeo.com/video/{vimeo_id}', url),
            VimeoIE, vimeo_id)
