import functools

from .common import InfoExtractor
from ..utils import (
    format_field,
    int_or_none,
    js_to_json,
    make_archive_id,
    url_basename,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class JioSaavnBaseIE(InfoExtractor):
    _VALID_BITRATES = ('16', '32', '64', '128', '320')

    @functools.cached_property
    def requested_bitrates(self):
        requested_bitrates = self._configuration_arg('bitrate', ['128', '320'], ie_key='JioSaavn')
        if invalid_bitrates := [br for br in requested_bitrates if br not in self._VALID_BITRATES]:
            raise ValueError(
                f'Invalid bitrate(s): {", ".join(invalid_bitrates)}. '
                + f'Valid bitrates are: {", ".join(self._VALID_BITRATES)}')
        return requested_bitrates

    def _extract_formats(self, song_data):
        for bitrate in self.requested_bitrates:
            media_data = self._download_json(
                'https://www.jiosaavn.com/api.php', song_data['id'],
                f'Downloading format info for {bitrate}',
                fatal=False, data=urlencode_postdata({
                    '__call': 'song.generateAuthToken',
                    '_format': 'json',
                    'bitrate': bitrate,
                    'url': song_data['encrypted_media_url'],
                }))
            if not traverse_obj(media_data, ('auth_url', {url_or_none})):
                self.report_warning(f'Unable to extract format info for {bitrate}')
                continue
            ext = media_data.get('type')
            yield {
                'url': media_data['auth_url'],
                'ext': 'm4a' if ext == 'mp4' else ext,
                'format_id': bitrate,
                'abr': int(bitrate),
                'vcodec': 'none',
            }

    def _extract_song(self, song_data, extract_flat=False):
        info = traverse_obj(song_data, {
            'id': ('id', {str}),
            'title': ('title', 'text', {str}),
            'album': ('album', 'text', {str}),
            'thumbnail': ('image', 0, {url_or_none}),
            'duration': ('duration', {int_or_none}),
            'view_count': ('play_count', {int_or_none}),
            'release_year': ('year', {int_or_none}),
            'artists': ('artists', lambda _, v: v['role'] == 'singer', 'name', {str}),
            'webpage_url': ('perma_url', {url_or_none}),  # for song, playlist extraction
        })
        if not info.get('webpage_url'):  # for album extraction / fallback
            info['webpage_url'] = format_field(
                song_data, [('title', 'action')], 'https://www.jiosaavn.com%s') or None
        if webpage_url := info['webpage_url']:
            info['_old_archive_ids'] = [make_archive_id(JioSaavnSongIE, url_basename(webpage_url))]
        if not extract_flat:
            info.update({
                'formats': list(self._extract_formats(song_data)),
                'extractor': JioSaavnSongIE.IE_NAME,
                'extractor_key': JioSaavnSongIE.ie_key(),
            })
        return info

    def _entries(self, playlist_data):
        for song_data in traverse_obj(playlist_data, self._PATH):
            song_info = self._extract_song(song_data, extract_flat=True)
            yield self.url_result(song_info['webpage_url'], JioSaavnSongIE, **song_info)

    def _extract_initial_data(self, url, display_id):
        webpage = self._download_webpage(url, display_id)
        return self._search_json(
            r'window\.__INITIAL_DATA__\s*=', webpage,
            'initial data', display_id, transform_source=js_to_json)


class JioSaavnSongIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:song'
    _VALID_URL = r'https?://(?:www\.)?(?:jiosaavn\.com/song/[^/?#]+/|saavn\.com/s/song/(?:[^/?#]+/){3})(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/song/leja-re/OQsEfQFVUXk',
        'md5': '3b84396d15ed9e083c3106f1fa589c04',
        'info_dict': {
            'id': 'IcoLuefJ',
            'ext': 'm4a',
            'title': 'Leja Re',
            'album': 'Leja Re',
            'thumbnail': 'https://c.saavncdn.com/258/Leja-Re-Hindi-2018-20181124024539-500x500.jpg',
            'duration': 205,
            'view_count': int,
            'release_year': 2018,
            'artists': ['Sandesh Shandilya', 'Dhvani Bhanushali', 'Tanishk Bagchi'],
            '_old_archive_ids': ['jiosaavnsong OQsEfQFVUXk'],
        },
    }, {
        'url': 'https://www.saavn.com/s/song/hindi/Saathiya/O-Humdum-Suniyo-Re/KAMiazoCblU',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        song_data = self._extract_initial_data(url, self._match_id(url))['song']['song']
        return self._extract_song(song_data)


class JioSaavnAlbumIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:album'
    _VALID_URL = r'https?://(?:www\.)?(?:jio)?saavn\.com/album/[^/?#]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/album/96/buIOjYZDrNA_',
        'info_dict': {
            'id': 'buIOjYZDrNA_',
            'title': '96',
        },
        'playlist_count': 10,
    }]
    _PATH = ('modules', lambda _, x: x['key'] == 'list', 'data', lambda _, v: v['title']['action'])

    def _real_extract(self, url):
        display_id = self._match_id(url)
        album_data = self._extract_initial_data(url, display_id)['albumView']

        return self.playlist_result(
            self._entries(album_data), display_id, traverse_obj(album_data, ('album', 'title', 'text', {str})))


class JioSaavnPlaylistIE(JioSaavnBaseIE):
    IE_NAME = 'jiosaavn:playlist'
    _VALID_URL = r'https?://(?:www\.)?(?:jio)?saavn\.com/s/playlist/(?:[^/?#]+/){2}(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/s/playlist/2279fbe391defa793ad7076929a2f5c9/mood-english/LlJ8ZWT1ibN5084vKHRj2Q__',
        'info_dict': {
            'id': 'LlJ8ZWT1ibN5084vKHRj2Q__',
            'title': 'Mood English',
        },
        'playlist_mincount': 50,
    }]
    _PATH = ('list', lambda _, v: v['perma_url'])

    def _real_extract(self, url):
        display_id = self._match_id(url)
        playlist_data = self._extract_initial_data(url, display_id)['playlist']['playlist']

        return self.playlist_result(
            self._entries(playlist_data), display_id, traverse_obj(playlist_data, ('title', 'text', {str})))
