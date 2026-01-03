from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import (
    parse_iso8601,
    smuggle_url,
)
from ..utils.traversal import traverse_obj


class CroatianFilmIE(InfoExtractor):
    IE_NAME = 'croatian.film'
    _VALID_URL = r'https://?(?:www\.)?croatian\.film/[a-z]{2}/[^/?#]+/(?P<id>\d+)'
    _GEO_COUNTRIES = ['HR']

    _TESTS = [{
        'url': 'https://www.croatian.film/en/films/74757',
        'info_dict': {
            'id': '1131431769',
            'title': '\u201dPOTOP\u201d, r. Kristijan Krajn\u010dan , (EN + HRsub)',
            'uploader': 'croatian.film',
            'uploader_id': 'user94192658',
            'uploader_url': 'https://vimeo.com/user94192658',
            'duration': 937,
            'views': 119,
            'year': 2019,
        },
    }, {
        'url': 'https://www.croatian.film/en/films/77144',
        'only_matching': True,
    }, {
        'url': 'https://www.croatian.film/en/films/75904/watch',
        'only_matching': True,
    }]

    def _extract_thumbnails(self, data):
        thumbnails = []
        if pictures := data.get('pictures'):
            for name, thumb_url in pictures.items():
                height, weight = self._search_regex(
                    r'(?P<height>\d+)x(?P<weight>\d+)',
                    thumb_url, 'height&weight', group=('height', 'weight'), fatal=False)
                thumbnails.append({
                    'url': thumb_url,
                    'id': str(name),
                    'height': int(height) if height else None,
                    'width': int(weight) if weight else None,
                })
        if data.get('cover'):
            thumbnails.append({
                'url': data['cover'],
                'id': 'cover',
            })
        if data.get('listingImage'):
            thumbnails.append({
                'url': data['listingImage'],
                'id': 'listingImage',
            })

        return thumbnails

    def _extract_metadata(self, data):
        return {
            **traverse_obj(data, ({
                'duration': ('duration', {int}),
                'views': ('views', {int}),
                'year': ('year', {int}),
                'age': ('ageCategory', {int}),
                'timestamp': ('createdAt', {parse_iso8601}),
            })),
            'thumbnails': self._extract_thumbnails(data),
        }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        vimeo_info = self._download_json(
            f'https://api.croatian.film/api/videos/{display_id}',
            display_id)['video']

        if errors := traverse_obj(vimeo_info, ('errors', lambda _, v: v['code'])):
            codes = traverse_obj(errors, (..., 'code', {str}))
            if 'INVALID_COUNTRY' in codes:
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            raise ExtractorError(join_nonempty(
                *(traverse_obj(errors, (..., 'details', {str})) or codes),
                delim='; '))

        vimeo_id = vimeo_info.get('vimeoURL')
        vimeo_id = vimeo_id.replace('/videos/', '') if '/videos/' else vimeo_id
        return self.url_result(
            smuggle_url(f'https://player.vimeo.com/video/{vimeo_id}', {'referer': url}),
            VimeoIE, vimeo_id, **self._extract_metadata(vimeo_info))
