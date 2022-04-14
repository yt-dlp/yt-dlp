from .common import InfoExtractor


class M6IE(InfoExtractor):
    IE_NAME = 'm6'
    _VALID_URL = r'https?://(?:www\.)?m6\.fr/[^/]+/videos/(?P<id>\d+)-[^\.]+\.html'

    _TEST = {
        'url': 'http://www.m6.fr/emission-les_reines_du_shopping/videos/11323908-emeline_est_la_reine_du_shopping_sur_le_theme_ma_fete_d_8217_anniversaire.html',
        'md5': '242994a87de2c316891428e0176bcb77',
        'info_dict': {
            'id': '11323908',
            'ext': 'mp4',
            'title': 'Emeline est la Reine du Shopping sur le thème « Ma fête d’anniversaire ! »',
            'description': 'md5:1212ae8fb4b7baa4dc3886c5676007c2',
            'duration': 100,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result('6play:%s' % video_id, 'SixPlay', video_id)
