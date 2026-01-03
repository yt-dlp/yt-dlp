from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import (
    ExtractorError,
    join_nonempty,
    smuggle_url,
)
from ..utils.traversal import traverse_obj


class CroatianFilmIE(InfoExtractor):
    IE_NAME = 'croatian.film'
    _VALID_URL = r'https://?(?:www\.)?croatian\.film/[a-z]{2}/[^/?#]+/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.croatian.film/en/films/74757',
        'info_dict': {
            'id': '1131431769',
            'title': '\u201dPOTOP\u201d, r. Kristijan Krajn\u010dan , (EN + HRsub)',
            'uploader': 'croatian.film',
            'uploader_id': 'user94192658',
            'uploader_url': 'https://vimeo.com/user94192658',
            'duration': 937,
        },
    }, {
        'url': 'https://www.croatian.film/en/films/77144',
        'only_matching': True,
    }, {
        'url': 'https://www.croatian.film/en/films/75904/watch',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        api_data = self._download_json(
            f'https://api.croatian.film/api/videos/{display_id}',
            display_id)

        if errors := traverse_obj(api_data, ('errors', lambda _, v: v['code'])):
            codes = traverse_obj(errors, (..., 'code', {str}))
            if 'INVALID_COUNTRY' in codes:
                self.raise_geo_restricted(countries=['hr'])
            raise ExtractorError(join_nonempty(
                *(traverse_obj(errors, (..., 'details', {str})) or codes),
                delim='; '))

        vimeo_id = self._search_regex(
            r'/videos/(\d+)', api_data['video']['vimeoURL'], 'vimeo ID')

        return self.url_result(
            VimeoIE._smuggle_referrer(f'https://player.vimeo.com/video/{vimeo_id}', url),
            VimeoIE, vimeo_id)
