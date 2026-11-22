from .common import InfoExtractor
from ..utils import clean_html
from ..utils.traversal import (
    find_element,
    find_elements,
    traverse_obj,
)


class FilmArchivIE(InfoExtractor):
    IE_DESC = 'FILMARCHIV ON'
    _VALID_URL = r'https?://(?:www\.)?filmarchiv\.at/de/filmarchiv-on/video/(?P<id>f_[0-9a-zA-Z]{5,})'
    _TESTS = [{
        'url': 'https://www.filmarchiv.at/de/filmarchiv-on/video/f_0305p7xKrXUPBwoNE9x6mh',
        'md5': '54a6596f6a84624531866008a77fa27a',
        'info_dict': {
            'id': 'f_0305p7xKrXUPBwoNE9x6mh',
            'ext': 'mp4',
            'title': 'Der Wurstelprater zur Kaiserzeit',
            'description': 'md5:9843f92df5cc9a4975cee7aabcf6e3b2',
            'thumbnail': r're:https://cdn\.filmarchiv\.at/f_0305/p7xKrXUPBwoNE9x6mh_v1/poster\.jpg',
        },
    }, {
        'url': 'https://www.filmarchiv.at/de/filmarchiv-on/video/f_0306vI3wO0tJIsfrqYFQXF',
        'md5': '595385d7f54cb6529140ee8de7d1c3c7',
        'info_dict': {
            'id': 'f_0306vI3wO0tJIsfrqYFQXF',
            'ext': 'mp4',
            'title': 'Vor 70 Jahren: Wettgehen der Briefträger in Wien',
            'description': 'md5:b2a2e4230923cd1969d471c552e62811',
            'thumbnail': r're:https://cdn\.filmarchiv\.at/f_0306/vI3wO0tJIsfrqYFQXF_v1/poster\.jpg',
        },
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)
        path = '/'.join((media_id[:6], media_id[6:]))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://cdn.filmarchiv.at/{path}_v1_sv1/playlist.m3u8', media_id)

        return {
            'id': media_id,
            'title': traverse_obj(webpage, ({find_element(tag='title-div')}, {clean_html})),
            'description': traverse_obj(webpage, (
                {find_elements(tag='div', attr='class', value=r'.*\bborder-base-content\b', regex=True)}, ...,
                {find_elements(tag='div', attr='class', value=r'.*\bprose\b', html=False, regex=True)}, ...,
                {clean_html}, any)),
            'thumbnail': f'https://cdn.filmarchiv.at/{path}_v1/poster.jpg',
            'formats': formats,
            'subtitles': subtitles,
        }
