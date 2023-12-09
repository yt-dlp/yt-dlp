import re

from .common import InfoExtractor


class Mx3IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mx3\.ch/t/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://mx3.ch/t/1Cru',
        'md5': '4aa5e93c3a2da01048e22d7851dc0a70',
        'info_dict': {
            'id': '1Cru',
            # This one is audio-only. Looks like an ordinary mp3.
            'ext': 'mp3',
            'artist': 'Tortue Tortue',
            'genre': 'Rock',
            'thumbnail': 'https://mx3.ch/pictures/mx3/file/0101/4643/square_large/1-s-envoler-1.jpg?1630272813',
            'title': 'Tortue Tortue - S\'envoler',
        }
    }, {
        'url': 'https://mx3.ch/t/1LIY',
        'md5': '87c856be272aa614febb9455aecb5833',
        'info_dict': {
            'id': '1LIY',
            # This is a music video. 'file' says: ISO Media, MP4 Base Media v1 [ISO 14496-12:2003]
            'ext': 'mp4',
            'artist': 'The Broots',
            'genre': 'Electro',
            'thumbnail': 'https://mx3.ch/pictures/mx3/file/0110/0003/video_large/frame_0000.png?1686963670',
            'title': 'The Broots - The Broots-Larytta remix "Begging For Help"',
        }
    }]

    def _real_extract(self, url):
        track_id = self._match_id(url)
        webpage = self._download_webpage(url, track_id)

        title = self._og_search_title(webpage)
        genre = self._html_search_regex(r'<div\b[^>]+class="single-band-genre"[^>]*>([^<]+)</div>',
                                        webpage, 'genre', fatal=False, flags=re.DOTALL)
        thumbnail = self._og_search_thumbnail(webpage)
        is_video = 'central-player-placeholder video' in webpage or '/video' in thumbnail

        if ' - ' in title:
            artist, _track = title.split(' - ', maxsplit=1)
        else:
            artist = None

        return {
            'id': track_id,
            'url': f'https://mx3.ch/tracks/{track_id}/player_asset',
            'ext': 'mp4' if is_video else 'mp3',
            'title': title,
            'artist': artist,
            'genre': genre,
            'thumbnail': thumbnail,
        }
