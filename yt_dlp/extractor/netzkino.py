from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class NetzkinoIE(InfoExtractor):
    _GEO_COUNTRIES = ['DE']
    _VALID_URL = r'https?://(?:www\.)?netzkino\.de/details/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.netzkino.de/details/snow-beast',
        'md5': '1a4c90fe40d3ccabce163287e45e56dd',
        'info_dict': {
            'id': 'snow-beast',
            'ext': 'mp4',
            'title': 'Snow Beast',
            'age_limit': 12,
            'alt_title': 'Snow Beast',
            'cast': 'count:3',
            'categories': 'count:7',
            'creators': 'count:2',
            'description': 'md5:e604a954a7f827a80e96a3a97d48b269',
            'location': 'US',
            'release_year': 2011,
            'thumbnail': r're:https?://.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        next_js_data = self._search_nextjs_data(webpage, video_id)

        query = traverse_obj(next_js_data, (
            'props', '__dehydratedState', 'queries', ..., 'state',
            'data', 'data', lambda _, v: v['__typename'] == 'CmsMovie', any))
        if 'DRM' in traverse_obj(query, ('licenses', 'nodes', ..., 'properties', {str})):
            self.report_drm(video_id)

        return {
            'id': video_id,
            **traverse_obj(query, {
                'title': ('originalTitle', {clean_html}),
                'age_limit': ('fskRating', {int_or_none}),
                'alt_title': ('originalTitle', {clean_html}, filter),
                'cast': ('cast', 'nodes', ..., 'person', 'name', {clean_html}, filter),
                'creators': (('directors', 'writers'), 'nodes', ..., 'person', 'name', {clean_html}, filter),
                'categories': ('categories', 'nodes', ..., 'category', 'title', {clean_html}, filter),
                'description': ('longSynopsis', {clean_html}, filter),
                'duration': ('runtimeInSeconds', {int_or_none}),
                'location': ('productionCountry', {clean_html}, filter),
                'release_year': ('productionYear', {int_or_none}),
                'thumbnail': ('coverImage', 'masterUrl', {url_or_none}),
                'url': ('videoSource', 'pmdUrl', {urljoin('https://pmd.netzkino-seite.netzkino.de/')}),
            }),
        }
