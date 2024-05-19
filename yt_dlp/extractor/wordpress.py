import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_elements_by_class,
    get_elements_text_and_html_by_attribute,
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
            yield self.playlist_result(entries, self._generic_id(url) + f'-wp-playlist-{i + 1}', 'Wordpress Playlist')


class WordpressMiniAudioPlayerEmbedIE(InfoExtractor):
    # WordPress MB Mini Player Plugin
    # https://wordpress.org/plugins/wp-miniaudioplayer/
    # Note: This is for the WordPress plugin version only.
    _VALID_URL = False
    IE_NAME = 'wordpress:mb.miniAudioPlayer'
    _WEBPAGE_TESTS = [{
        # Version 1.8.10: https://plugins.trac.wordpress.org/browser/wp-miniaudioplayer/tags/1.8.10
        'url': 'https://news.samsung.com/global/over-the-horizon-the-evolution-of-the-samsung-galaxy-brand-sound',
        'info_dict': {
            'id': 'over-the-horizon-the-evolution-of-the-samsung-galaxy-brand-sound',
            'title': 'Over the Horizon: The Evolution of the Samsung Galaxy Brand Sound',
            'age_limit': 0,
            'thumbnail': 'https://img.global.news.samsung.com/global/wp-content/uploads/2015/04/OTH_Main_Title-e1429612467870.jpg',
            'description': 'md5:bc3dd738d1f11d9232e94e6629983bf7',
        },
        'playlist': [{
            'info_dict': {
                'id': 'over_the_horizon_2013',
                'ext': 'mp3',
                'title': 'Over the Horizon 2013',
                'url': 'http://news.samsung.com/global/wp-content/uploads/ringtones/over_the_horizon_2013.mp3'
            }
        }],
        'playlist_count': 6,
        'params': {'skip_download': True}
    }, {
        # Version 1.9.3: https://plugins.trac.wordpress.org/browser/wp-miniaudioplayer/tags/1.9.3
        'url': 'https://www.booksontape.com/collections/audiobooks-with-teacher-guides/',
        'info_dict': {
            'id': 'audiobooks-with-teacher-guides',
            'title': 'Audiobooks with Teacher Guides | Books on Tape',
            'age_limit': 0,
            'thumbnail': 'https://www.booksontape.com/wp-content/uploads/2016/09/bot-logo-1200x630.jpg',
        },
        'playlist_mincount': 12
    }, {
        # Version 1.9.7: https://plugins.trac.wordpress.org/browser/wp-miniaudioplayer/tags/1.9.7
        # But has spaces around href filter
        'url': 'https://www.estudiords.com.br/temas/',
        'info_dict': {
            'id': 'temas',
            'title': 'Temas Variados',
            'age_limit': 0,
            'timestamp': float,
            'upload_date': str,
            'thumbnail': 'https://www.estudiords.com.br/wp-content/uploads/2021/03/LOGO-TEMAS.png',
            'description': 'md5:ab24d6a7ed0312ad2d466e721679f5a0',
        },
        'playlist_mincount': 30
    }]

    def _extract_from_webpage(self, url, webpage):
        # Common function for the WordPress plugin version only.
        mb_player_params = self._search_regex(
            r'function\s*initializeMiniAudioPlayer\(\){[^}]+jQuery([^;]+)\.mb_miniPlayer',
            webpage, 'mb player params', default=None)
        if not mb_player_params:
            return
        # v1.55 - 1.9.3 has "a[href*='.mp3'] ,a[href*='.m4a']"
        # v1.9.4+ has "a[href*='.mp3']" only
        file_exts = re.findall(r'a\[href\s*\*=\s*\'\.([a-zA-Z\d]+)\'', mb_player_params)
        if not file_exts:
            return

        candidates = get_elements_text_and_html_by_attribute(
            'href', rf'(?:[^\"\']+\.(?:{"|".join(file_exts)}))', webpage, escape_value=False, tag='a')

        for title, html in candidates:
            attrs = extract_attributes(html)
            # XXX: not tested - have not found any example of it being used
            if any(c in (attrs.get('class') or '') for c in re.findall(r'\.not\("\.([^"]+)', mb_player_params)):
                continue
            href = attrs['href']
            yield {
                'id': self._generic_id(href),
                'title': title or self._generic_title(href),
                'url': href,
            }
