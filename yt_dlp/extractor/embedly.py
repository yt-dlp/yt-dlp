from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote


class EmbedlyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|cdn\.)?embedly\.com/widgets/media\.html\?(?:[^#]*?&)?url=(?P<id>[^#&]+)'
    _TESTS = [{
        'url': 'https://cdn.embedly.com/widgets/media.html?src=http%3A%2F%2Fwww.youtube.com%2Fembed%2Fvideoseries%3Flist%3DUUGLim4T2loE5rwCMdpCIPVg&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DSU4fj_aEMVw%26list%3DUUGLim4T2loE5rwCMdpCIPVg&image=http%3A%2F%2Fi.ytimg.com%2Fvi%2FSU4fj_aEMVw%2Fhqdefault.jpg&key=8ee8a2e6a8cc47aab1a5ee67f9a178e0&type=text%2Fhtml&schema=youtube&autoplay=1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(compat_urllib_parse_unquote(self._match_id(url)))
