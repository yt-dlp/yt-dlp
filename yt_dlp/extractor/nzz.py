import re

from .common import InfoExtractor


class NZZIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nzz\.ch/(?:[^/]+/)*[^/?#]+-ld\.(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.nzz.ch/zuerich/gymizyte/gymizyte-schreiben-schueler-heute-noch-diktate-ld.9153',
        'info_dict': {
            'id': '9153',
        },
        'playlist_mincount': 6,
    }, {
        'url': 'https://www.nzz.ch/video/nzz-standpunkte/cvp-auf-der-suche-nach-dem-mass-der-mitte-ld.1368112',
        'info_dict': {
            'id': '1368112',
        },
        'playlist_count': 1,
    }]

    def _entries(self, webpage, page_id):
        for script in re.findall(r'(?s)<script[^>]* data-hid="jw-video-jw[^>]+>(.+?)</script>', webpage):
            settings = self._search_json(r'var\s+settings\s*=[^{]*', script, 'settings', page_id, fatal=False)
            if entry := self._parse_jwplayer_data(settings, page_id):
                yield entry

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        return self.playlist_result(self._entries(webpage, page_id), page_id)
