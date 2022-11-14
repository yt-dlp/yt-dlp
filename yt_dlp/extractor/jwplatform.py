import re

from .common import InfoExtractor
from ..utils import unsmuggle_url


class JWPlatformIE(InfoExtractor):
    _VALID_URL = r'(?:https?://(?:content\.jwplatform|cdn\.jwplayer)\.com/(?:(?:feed|player|thumb|preview|manifest)s|jw6|v2/media)/|jwplatform:)(?P<id>[a-zA-Z0-9]{8})'
    _TESTS = [{
        'url': 'http://content.jwplatform.com/players/nPripu9l-ALJ3XQCI.js',
        'md5': 'fa8899fa601eb7c83a64e9d568bdf325',
        'info_dict': {
            'id': 'nPripu9l',
            'ext': 'mov',
            'title': 'Big Buck Bunny Trailer',
            'description': 'Big Buck Bunny is a short animated film by the Blender Institute. It is made using free and open source software.',
            'upload_date': '20081127',
            'timestamp': 1227796140,
        }
    }, {
        'url': 'https://cdn.jwplayer.com/players/nPripu9l-ALJ3XQCI.js',
        'only_matching': True,
    }]

    _WEBPAGE_TESTS = [{
        # JWPlatform iframe
        'url': 'https://www.covermagazine.co.uk/feature/2465255/business-protection-involved',
        'info_dict': {
            'id': 'AG26UQXM',
            'ext': 'mp4',
            'upload_date': '20160719',
            'timestamp': 1468923808,
            'title': '2016_05_18 Cover L&G Business Protection V1 FINAL.mp4',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/AG26UQXM/poster.jpg?width=720',
            'description': '',
            'duration': 294.0,
        },
    }, {
        # Player url not surrounded by quotes
        'url': 'https://www.deutsche-kinemathek.de/en/online/streaming/darling-berlin',
        'info_dict': {
            'id': 'R10NQdhY',
            'title': 'Playgirl',
            'ext': 'mp4',
            'upload_date': '20220624',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/R10NQdhY/poster.jpg?width=720',
            'timestamp': 1656064800,
            'description': 'BRD 1966, Will Tremper',
            'duration': 5146.0,
        },
        'params': {'allowed_extractors': ['generic', 'jwplatform']},
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for tag, key in ((r'(?:script|iframe)', 'src'), ('input', 'value')):
            # <input value=URL> is used by hyland.com
            # if we find <iframe>, dont look for <input>
            ret = re.findall(
                r'<%s[^>]+?%s=["\']?((?:https?:)?//(?:content\.jwplatform|cdn\.jwplayer)\.com/players/[a-zA-Z0-9]{8})' % (tag, key),
                webpage)
            if ret:
                return ret
        mobj = re.search(r'<div\b[^>]* data-video-jw-id="([a-zA-Z0-9]{8})"', webpage)
        if mobj:
            return [f'jwplatform:{mobj.group(1)}']

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        self._initialize_geo_bypass({
            'countries': smuggled_data.get('geo_countries'),
        })
        video_id = self._match_id(url)
        json_data = self._download_json('https://cdn.jwplayer.com/v2/media/' + video_id, video_id)
        return self._parse_jwplayer_data(json_data, video_id)
