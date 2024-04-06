from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    orderedSet,
    url_or_none,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import traverse_obj


class JioSaavnBaseIE(InfoExtractor):
    def _extract_initial_data(self, url, audio_id):
        webpage = self._download_webpage(url, audio_id)
        return self._search_json(
            r'window\.__INITIAL_DATA__\s*=', webpage,
            'init json', audio_id, transform_source=js_to_json)


class JioSaavnSongIE(JioSaavnBaseIE):
    _VALID_URL = r'https?://(?:www\.)?(?:jiosaavn\.com/song/[^/?#]+/|saavn\.com/s/song/(?:[^/?#]+/){3})(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/song/leja-re/OQsEfQFVUXk',
        'md5': '3b84396d15ed9e083c3106f1fa589c04',
        'info_dict': {
            'id': 'OQsEfQFVUXk',
            'ext': 'm4a',
            'title': 'Leja Re',
            'album': 'Leja Re',
            'thumbnail': 'https://c.saavncdn.com/258/Leja-Re-Hindi-2018-20181124024539-500x500.jpg',
            'duration': 205,
            'view_count': int,
            'release_year': 2018,
            'artists': ['Sandesh Shandilya', 'Dhvani Bhanushali', 'Tanishk Bagchi', 'Rashmi Virag', 'Irshad Kamil'],
        },
    }, {
        'url': 'https://www.saavn.com/s/song/hindi/Saathiya/O-Humdum-Suniyo-Re/KAMiazoCblU',
        'only_matching': True,
    }]

    _VALID_BITRATES = ('16', '32', '64', '128', '320')

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        extract_bitrates = self._configuration_arg('bitrate', ['128', '320'], ie_key='JioSaavn')
        if invalid_bitrates := [br for br in extract_bitrates if br not in self._VALID_BITRATES]:
            raise ValueError(
                f'Invalid bitrate(s): {", ".join(invalid_bitrates)}. '
                + f'Valid bitrates are: {", ".join(self._VALID_BITRATES)}')

        song_data = self._extract_initial_data(url, audio_id)['song']['song']
        formats = []
        for bitrate in extract_bitrates:
            media_data = self._download_json(
                'https://www.jiosaavn.com/api.php', audio_id, f'Downloading format info for {bitrate}',
                fatal=False, data=urlencode_postdata({
                    '__call': 'song.generateAuthToken',
                    '_format': 'json',
                    'bitrate': bitrate,
                    'url': song_data['encrypted_media_url'],
                }))
            if not media_data.get('auth_url'):
                self.report_warning(f'Unable to extract format info for {bitrate}')
                continue
            ext = media_data.get('type')
            formats.append({
                'url': media_data['auth_url'],
                'ext': 'm4a' if ext == 'mp4' else ext,
                'format_id': bitrate,
                'abr': int(bitrate),
                'vcodec': 'none',
            })

        return {
            'id': audio_id,
            'formats': formats,
            **traverse_obj(song_data, {
                'title': ('title', 'text'),
                'album': ('album', 'text'),
                'thumbnail': ('image', 0, {url_or_none}),
                'duration': ('duration', {int_or_none}),
                'view_count': ('play_count', {int_or_none}),
                'release_year': ('year', {int_or_none}),
                'artists': ('artists', ..., 'name', {str}, all, {orderedSet}),
            }),
        }


class JioSaavnAlbumIE(JioSaavnBaseIE):
    _VALID_URL = r'https?://(?:www\.)?(?:jio)?saavn\.com/album/[^/?#]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.jiosaavn.com/album/96/buIOjYZDrNA_',
        'info_dict': {
            'id': 'buIOjYZDrNA_',
            'title': '96',
        },
        'playlist_count': 10,
    }]

    def _real_extract(self, url):
        album_id = self._match_id(url)
        album_view = self._extract_initial_data(url, album_id)['albumView']

        return self.playlist_from_matches(
            traverse_obj(album_view, (
                'modules', lambda _, x: x['key'] == 'list', 'data', ..., 'title', 'action', {str})),
            album_id, traverse_obj(album_view, ('album', 'title', 'text', {str})), ie=JioSaavnSongIE,
            getter=lambda x: urljoin('https://www.jiosaavn.com/', x))
