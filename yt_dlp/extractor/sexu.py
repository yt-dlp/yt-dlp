from .common import InfoExtractor


class SexuIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?sexu\.com/(?P<id>\d+)'
    _TEST = {
        'url': 'http://sexu.com/961791/',
        'md5': 'ff615aca9691053c94f8f10d96cd7884',
        'info_dict': {
            'id': '961791',
            'ext': 'mp4',
            'title': 'md5:4d05a19a5fc049a63dbbaf05fb71d91b',
            'description': 'md5:2b75327061310a3afb3fbd7d09e2e403',
            'categories': list,  # NSFW
            'thumbnail': r're:https?://.*\.jpg$',
            'age_limit': 18,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        jwvideo = self._parse_json(
            self._search_regex(r'\.setup\(\s*({.+?})\s*\);', webpage, 'jwvideo'),
            video_id)

        sources = jwvideo['sources']

        formats = [{
            'url': source['file'].replace('\\', ''),
            'format_id': source.get('label'),
            'height': int(self._search_regex(
                r'^(\d+)[pP]', source.get('label', ''), 'height',
                default=None)),
        } for source in sources if source.get('file')]

        title = self._html_search_regex(
            r'<title>([^<]+)\s*-\s*Sexu\.Com</title>', webpage, 'title')

        description = self._html_search_meta(
            'description', webpage, 'description')

        thumbnail = jwvideo.get('image')

        categories_str = self._html_search_meta(
            'keywords', webpage, 'categories')
        categories = (
            None if categories_str is None
            else categories_str.split(','))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'categories': categories,
            'formats': formats,
            'age_limit': 18,
        }
