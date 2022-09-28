from .common import InfoExtractor
from ..utils import (
    get_elements_by_class,
    int_or_none,
    parse_duration,
    traverse_obj,
)


# https://codex.wordpress.org/Playlist_Shortcode
class WordpressPlaylistEmbedIE(InfoExtractor):
    _VALID_URL = False
    IE_NAME = 'wordpress:playlist'
    _WEBPAGE_TESTS = [{
        # 5 WordPress playlists. This is using wpse-playlist, which is similar.
        # See: https://github.com/birgire/wpse-playlist
        'url': 'https://xlino.com/wordpress-playlist-shortcode-with-external-audio-or-video-files/',
        'info_dict': {
            'id': 'wordpress-playlist-shortcode-with-external-audio-or-video-files',
            'title': 'WordPress: Playlist shortcode with external audio or video files – Birgir Erlendsson (birgire)',
            'age_limit': 0,
        },
        'playlist_count': 5,
    }, {
        'url': 'https://pianoadventures.com/products/piano-adventures-level-1-lesson-book-enhanced-cd/',
        'info_dict': {
            'id': 'piano-adventures-level-1-lesson-book-enhanced-cd-wp-playlist-1',
            'title': 'Wordpress Playlist',
            'thumbnail': 'https://pianoadventures.com/wp-content/uploads/sites/13/2022/01/CD1002cover.jpg',
            'age_limit': 0,
        },
        'playlist': [{
            'info_dict': {
                'id': 'CD1002-21',
                'ext': 'mp3',
                'title': '21 Half-Time Show',
                'thumbnail': 'https://pianoadventures.com/wp-content/plugins/media-library-assistant/images/crystal/audio.png',
                'album': 'Piano Adventures Level 1 Lesson Book (2nd Edition)',
                'genre': 'Classical',
                'duration': 49.0,
                'artist': 'Nancy and Randall Faber',
                'description': 'md5:a9f8e9aeabbd2912bc13cc0fab1a4ce8',
            }
        }],
        'playlist_count': 6,
        'params': {'skip_download': True}
    }]

    def _extract_from_webpage(self, url, webpage):
        # class should always be "wp-playlist-script"
        # See: https://core.trac.wordpress.org/browser/trunk/src/wp-includes/media.php#L2930
        for i, j in enumerate(get_elements_by_class('wp-playlist-script', webpage)):
            playlist_json = self._parse_json(j, self._generic_id(url), fatal=False, ignore_extra=True, errnote='') or {}
            if not playlist_json:
                continue
            entries = [{
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
            } for track in traverse_obj(playlist_json, ('tracks', ...), expected_type=dict)]
            yield self.playlist_result(entries, self._generic_id(url) + f'-wp-playlist-{i+1}', 'Wordpress Playlist')
