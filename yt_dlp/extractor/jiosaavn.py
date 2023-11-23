from .common import InfoExtractor
from ..utils import (
    js_to_json,
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
        'md5': '7b1f70de088ede3a152ea34aece4df42',
        'info_dict': {
            'id': 'OQsEfQFVUXk',
            'ext': 'mp3',
            'title': 'Leja Re',
            'album': 'Leja Re',
            'thumbnail': 'https://c.saavncdn.com/258/Leja-Re-Hindi-2018-20181124024539-500x500.jpg',
        },
    }, {
        'url': 'https://www.saavn.com/s/song/hindi/Saathiya/O-Humdum-Suniyo-Re/KAMiazoCblU',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        song_data = self._extract_initial_data(url, audio_id)['song']['song']
        media_data = self._download_json(
            'https://www.jiosaavn.com/api.php', audio_id, data=urlencode_postdata({
                '__call': 'song.generateAuthToken',
                '_format': 'json',
                'bitrate': '128',
                'url': song_data['encrypted_media_url'],
            }))

        return {
            'id': audio_id,
            'url': media_data['auth_url'],
            'ext': media_data.get('type'),
            'vcodec': 'none',
            **traverse_obj(song_data, {
                'title': ('title', 'text'),
                'album': ('album', 'text'),
                'thumbnail': ('image', 0, {url_or_none}),
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
