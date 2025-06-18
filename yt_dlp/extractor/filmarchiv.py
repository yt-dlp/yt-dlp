from .common import InfoExtractor
from ..utils import clean_html
from ..utils.traversal import find_elements, traverse_obj


class FilmArchivIE(InfoExtractor):
    IE_NAME = 'FILMARCHIV ON'
    _VALID_URL = r'https?://(?:www\.)?filmarchiv\.at/de/filmarchiv-on/video/(?P<id>[0-9a-zA-Z_]+)'
    _TESTS = [{
        'url': 'https://www.filmarchiv.at/de/filmarchiv-on/video/f_0305p7xKrXUPBwoNE9x6mh',
        'md5': '54a6596f6a84624531866008a77fa27a',
        'info_dict': {
            'id': 'f_0305p7xKrXUPBwoNE9x6mh',
            'ext': 'mp4',
            'title': 'Der Wurstelprater zur Kaiserzeit',
            'description': 'md5:9843f92df5cc9a4975cee7aabcf6e3b2',
            'thumbnail': r're:https://cdn.filmarchiv.at/f_0305/p7xKrXUPBwoNE9x6mh[^/]*/poster.jpg$',
        },
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)

        title = self._html_search_regex(
            r'<title-div[^>]*>\s*(.+?)\s*</title-div>',
            webpage, 'title')

        description = traverse_obj(webpage, (
            {find_elements(
                tag='div',
                attr='class', value=r'[^\'"]*(?<=[\'"\s])border-base-content(?=[\'"\s])[^\'"]*',
                html=False, regex=True)}, ...,
            {find_elements(
                tag='div',
                attr='class', value=r'[^\'"]*(?<=[\'"\s])prose(?=[\'"\s])[^\'"]*',
                html=False, regex=True)}, ...,
            {clean_html}, any,
        ))

        og_img = self._html_search_meta('og:image', webpage, 'image URL', fatal=True)
        prefix = self._search_regex(
            r'/videostatic/([^/]+/[^_]+_[^/]+)/poster.jpg', og_img, 'prefix')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://cdn.filmarchiv.at/{prefix}_sv1/playlist.m3u8', media_id)

        return {
            'id': media_id,
            'title': title,
            'description': description,
            'thumbnail': f'https://cdn.filmarchiv.at/{prefix}/poster.jpg',
            'formats': formats,
            'subtitles': subtitles,
        }
