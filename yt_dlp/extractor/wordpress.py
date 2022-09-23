from .common import InfoExtractor
from ..utils import (
    get_elements_by_class,
    int_or_none,
    parse_duration,
    traverse_obj,
)


class WordpressPlaylistEmbedIE(InfoExtractor):
    _VALID_URL = False

    _WEBPAGE_TESTS = [{
        # TODO: fix
        'url': 'https://xlino.com/wordpress-playlist-shortcode-with-external-audio-or-video-files/',
        'info_dict': {
            'id': 'wordpress-playlist-shortcode-with-external-audio-or-video-files',
            'title': 'WordPress: Playlist shortcode with external audio or video files – Birgir Erlendsson (birgire)',
        },
        'playlist_mincount': 5,
    }, {
        'url': 'https://pianoadventures.com/products/piano-adventures-level-1-lesson-book-enhanced-cd/',
        'info_dict': {
            'id': 'piano-adventures-level-1-lesson-book-enhanced-cd-wp-playlist-1',
            'title': 'Wordpress Playlist',
            'thumbnail': 'https://pianoadventures.com/wp-content/uploads/sites/13/2022/01/CD1002cover.jpg',
            'age_limit': 0,
        },
        'playlist_mincount': 6,
    }]

    def _extract_from_webpage(self, url, webpage):
        # TODO: make work for multiple of these
        for i, j in enumerate(get_elements_by_class('wp-playlist-script', webpage)):
            playlist_json = self._parse_json(j, self._generic_id(url), fatal=False, ignore_extra=True, errnote='') or {}
            if not playlist_json:
                continue
            playlist_json = self._search_json(
                r'<script[^>]+type="application\/json"\s*class="wp-playlist-script"[^>]*>',
                webpage, 'wordpress playlist', self._generic_id(url), default=None)
            if not playlist_json:
                continue
            entries = []
            for track in playlist_json.get('tracks') or []:
                if not isinstance(track, dict):
                    continue
                entries.append({
                    'id': self._generic_id(track['src']),
                    'title': track.get('title'),
                    'url': track.get('src'),
                    'thumbnail': traverse_obj(track, ('thumb', 'src')),
                    'album': traverse_obj(track, ('meta', 'album')),
                    'artist': traverse_obj(track, ('meta', 'artist')),
                    'genre': traverse_obj(track, ('meta', 'genre')),
                    'duration': parse_duration(traverse_obj(track, ('meta', 'length_formatted'))),
                    'description': track.get('description'),
                    'height': int_or_none(traverse_obj(track, ('dimensions', 'original', 'height'))),
                    'width': int_or_none(traverse_obj(track, ('dimensions', 'original', 'width'))),
                })

            yield self.playlist_result(entries, self._generic_id(url) + f'-wp-playlist-{i+1}', 'Wordpress Playlist')
