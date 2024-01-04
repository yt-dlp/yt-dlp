from .common import InfoExtractor
from ..utils import (
    get_element_html_by_class,
)


class TurboIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?turbo\.fr/((?P<playlist>[_\d\w]+).xml)?'
    _API_URL = 'https://www.viously.com/video/hls/{0:}/index.m3u8'
    _TEST = {
        'url': 'http://www.turbo.fr/videos-voiture/454443-turbo-du-07-09-2014-renault-twingo-3-bentley-continental-gt-speed-ces-guide-achat-dacia.html',
        'md5': '37a6c3381599381ff53a7e1e0575c0bc',
        'info_dict': {
            'id': 'F_xQzS2jwb3',
            'ext': 'mp4',
            'title': 'Turbo du 07/09/2014 : Renault Twingo 3, Bentley Continental GT Speed, CES, Guide Achat Dacia...',
            'description': 'Turbo du 07/09/2014 : Renault Twingo 3, Bentley Continental GT Speed, CES, Guide Achat Dacia...',
        }
    }

    def _entries(self, playlist):
        items = playlist.findall('./channel/item')
        for item in items:
            if item is None or item.find('./link').text is None:
                continue
            yield self._extract_video(item.find('./link').text)

    def _extract_video(self, url):
        webpage = self._download_webpage(url, None)
        viously_player = get_element_html_by_class('viously-player-wrapper', webpage)
        video_id = self._html_search_regex(r'id="([-_\w]+)"', viously_player, 'video_id')
        title = self._html_extract_title(webpage)
        return {
            'id': video_id,
            'title': title,
            'description': title,
            'formats': self._extract_m3u8_formats(self._API_URL.format(video_id), video_id),
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        playlist_id = mobj.group('playlist')

        if playlist_id and self._yes_playlist(playlist_id, None):
            playlist = self._download_xml(url, playlist_id)
            return self.playlist_result(
                self._entries(playlist),
                playlist_id,
                playlist_title=playlist.find('./channel/title').text,
            )

        return self._extract_video(url)
