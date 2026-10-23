import re

from .common import InfoExtractor
from ..utils import unsmuggle_url


class JWPlatformIE(InfoExtractor):
    _VALID_URL = r'(?:https?://(?:content\.jwplatform|cdn\.jwplayer)\.com/(?:(?:feed|player|thumb|preview|manifest)s|jw6|v2/media)/|jwplatform:)(?P<id>[a-zA-Z0-9]{8})'
    _TESTS = [{
        'url': 'http://content.jwplatform.com/players/nPripu9l-ALJ3XQCI.js',
        'info_dict': {
            'id': 'nPripu9l',
            'ext': 'mp4',
            'title': 'Big Buck Bunny Trailer',
            'description': 'Big Buck Bunny is a short animated film by the Blender Institute. It is made using free and open source software.',
            'upload_date': '20081127',
            'timestamp': 1227796140,
            'duration': 32.0,
            'thumbnail': r're:https?://cdn\.jwplayer\.com/v2/media/.+',
        },
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
            'thumbnail': r're:https?://cdn\.jwplayer\.com/v2/media/.+',
            'description': '',
            'duration': 294.0,
        },
        'skip': 'Site no longer embeds JWPlatform',
    }, {
        # Player url not surrounded by quotes
        'url': 'https://www.deutsche-kinemathek.de/en/online/streaming/school-trip',
        'info_dict': {
            'id': 'jUxh5uin',
            'title': 'Klassenfahrt',
            'ext': 'mp4',
            'upload_date': '20230109',
            'thumbnail': r're:https?://cdn\.jwplayer\.com/v2/media/.+',
            'timestamp': 1673270298,
            'description': '',
            'duration': 5193.0,
        },
        'skip': 'Site no longer embeds JWPlatform',
    }, {
        # iframe src attribute includes backslash before URL string
        'url': 'https://www.elespectador.com/colombia/video-asi-se-evito-la-fuga-de-john-poulos-presunto-feminicida-de-valentina-trespalacios-explicacion',
        'info_dict': {
            'id': 'QD3gsexj',
            'title': 'Así se evitó la fuga de John Poulos, presunto feminicida de Valentina Trespalacios',
            'ext': 'mp4',
            'upload_date': '20230127',
            'thumbnail': r're:https?://cdn\.jwplayer\.com/v2/media/.+',
            'timestamp': 1674862986,
            'description': 'md5:128fd74591c4e1fc2da598c5cb6f5ce4',
            'duration': 263.0,
        },
    }, {
        'url': 'https://www.skimag.com/video/ski-people-1980',
        'info_dict': {
            'id': 'YTmgRiNU',
            'ext': 'mp4',
            'title': 'Ski People (1980)',
            'channel': 'snow',
            'description': 'md5:cf9c3d101452c91e141f292b19fe4843',
            'duration': 5688.0,
            'thumbnail': r're:https?://cdn\.jwplayer\.com/v2/media/.+',
            'timestamp': 1610407738,
            'upload_date': '20210111',
        },
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for tag, key in ((r'(?:script|iframe)', 'src'), ('input', 'value')):
            # <input value=URL> is used by hyland.com
            # if we find <iframe>, dont look for <input>
            ret = re.findall(
                rf'<{tag}[^>]+?{key}=\\?["\']?((?:https?:)?//(?:content\.jwplatform|cdn\.jwplayer)\.com/players/[a-zA-Z0-9]{{8}})',
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
