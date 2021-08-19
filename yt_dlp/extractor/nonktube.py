from __future__ import unicode_literals

from .nuevo import NuevoBaseIE


class NonkTubeIE(NuevoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?nonktube\.com/(?:(?:video|embed)/|media/nuevo/embed\.php\?.*?\bid=)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.nonktube.com/video/118636/sensual-wife-uncensored-fucked-in-hairy-pussy-and-facialized',
        'info_dict': {
            'id': '118636',
            'ext': 'mp4',
            'title': 'Sensual Wife Uncensored Fucked In Hairy Pussy And Facialized',
            'age_limit': 18,
            'duration': 1150.98,
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'https://www.nonktube.com/embed/118636',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(webpage)
        info = self._parse_html5_media_entries(url, webpage, video_id)[0]

        info.update({
            'id': video_id,
            'title': title,
            'age_limit': 18,
        })
        return info
