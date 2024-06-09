import hashlib
import random

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    try_get,
)


class JamendoIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            licensing\.jamendo\.com/[^/]+|
                            (?:www\.)?jamendo\.com
                        )
                        /track/(?P<id>[0-9]+)(?:/(?P<display_id>[^/?#&]+))?
                    '''
    _TESTS = [{
        'url': 'https://www.jamendo.com/track/196219/stories-from-emona-i',
        'md5': '6e9e82ed6db98678f171c25a8ed09ffd',
        'info_dict': {
            'id': '196219',
            'display_id': 'stories-from-emona-i',
            'ext': 'flac',
            # 'title': 'Maya Filipič - Stories from Emona I',
            'title': 'Stories from Emona I',
            'artist': 'Maya Filipič',
            'album': 'Between two worlds',
            'track': 'Stories from Emona I',
            'duration': 210,
            'thumbnail': 'https://usercontent.jamendo.com?type=album&id=29279&width=300&trackid=196219',
            'timestamp': 1217438117,
            'upload_date': '20080730',
            'license': 'by-nc-nd',
            'view_count': int,
            'like_count': int,
            'average_rating': int,
            'tags': ['piano', 'peaceful', 'newage', 'strings', 'upbeat'],
        },
    }, {
        'url': 'https://licensing.jamendo.com/en/track/1496667/energetic-rock',
        'only_matching': True,
    }]

    def _call_api(self, resource, resource_id, fatal=True):
        path = f'/api/{resource}s'
        rand = str(random.random())
        return self._download_json(
            'https://www.jamendo.com' + path, resource_id, fatal=fatal, query={
                'id[]': resource_id,
            }, headers={
                'X-Jam-Call': f'${hashlib.sha1((path + rand).encode()).hexdigest()}*{rand}~',
            })[0]

    def _real_extract(self, url):
        track_id, display_id = self._match_valid_url(url).groups()
        # webpage = self._download_webpage(
        #     'https://www.jamendo.com/track/' + track_id, track_id)
        # models = self._parse_json(self._html_search_regex(
        #     r"data-bundled-models='([^']+)",
        #     webpage, 'bundled models'), track_id)
        # track = models['track']['models'][0]
        track = self._call_api('track', track_id)
        title = track_name = track['name']
        # get_model = lambda x: try_get(models, lambda y: y[x]['models'][0], dict) or {}
        # artist = get_model('artist')
        # artist_name = artist.get('name')
        # if artist_name:
        #     title = '%s - %s' % (artist_name, title)
        # album = get_model('album')
        artist = self._call_api('artist', track.get('artistId'), fatal=False)
        album = self._call_api('album', track.get('albumId'), fatal=False)

        formats = [{
            'url': f'https://{sub_domain}.jamendo.com/?trackid={track_id}&format={format_id}&from=app-97dab294',
            'format_id': format_id,
            'ext': ext,
            'quality': quality,
        } for quality, (format_id, sub_domain, ext) in enumerate((
            ('mp31', 'mp3l', 'mp3'),
            ('mp32', 'mp3d', 'mp3'),
            ('ogg1', 'ogg', 'ogg'),
            ('flac', 'flac', 'flac'),
        ))]

        urls = []
        thumbnails = []
        for covers in (track.get('cover') or {}).values():
            for cover_id, cover_url in covers.items():
                if not cover_url or cover_url in urls:
                    continue
                urls.append(cover_url)
                size = int_or_none(cover_id.lstrip('size'))
                thumbnails.append({
                    'id': cover_id,
                    'url': cover_url,
                    'width': size,
                    'height': size,
                })

        tags = []
        for tag in (track.get('tags') or []):
            tag_name = tag.get('name')
            if not tag_name:
                continue
            tags.append(tag_name)

        stats = track.get('stats') or {}
        video_license = track.get('licenseCC') or []

        return {
            'id': track_id,
            'display_id': display_id,
            'thumbnails': thumbnails,
            'title': title,
            'description': track.get('description'),
            'duration': int_or_none(track.get('duration')),
            'artist': artist.get('name'),
            'track': track_name,
            'album': album.get('name'),
            'formats': formats,
            'license': '-'.join(video_license) if video_license else None,
            'timestamp': int_or_none(track.get('dateCreated')),
            'view_count': int_or_none(stats.get('listenedAll')),
            'like_count': int_or_none(stats.get('favorited')),
            'average_rating': int_or_none(stats.get('averageNote')),
            'tags': tags,
        }


class JamendoAlbumIE(JamendoIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?://(?:www\.)?jamendo\.com/album/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.jamendo.com/album/121486/duck-on-cover',
        'info_dict': {
            'id': '121486',
            'title': 'Duck On Cover',
            'description': 'md5:c2920eaeef07d7af5b96d7c64daf1239',
        },
        'playlist': [{
            'md5': 'e1a2fcb42bda30dfac990212924149a8',
            'info_dict': {
                'id': '1032333',
                'ext': 'flac',
                'title': 'Warmachine',
                'artist': 'Shearer',
                'track': 'Warmachine',
                'timestamp': 1368089771,
                'upload_date': '20130509',
                'view_count': int,
                'thumbnail': 'https://usercontent.jamendo.com?type=album&id=121486&width=300&trackid=1032333',
                'duration': 190,
                'license': 'by',
                'album': 'Duck On Cover',
                'average_rating': 4,
                'tags': ['rock', 'drums', 'bass', 'world', 'punk', 'neutral'],
                'like_count': int,
            },
        }, {
            'md5': '1f358d7b2f98edfe90fd55dac0799d50',
            'info_dict': {
                'id': '1032330',
                'ext': 'flac',
                'title': 'Without Your Ghost',
                'artist': 'Shearer',
                'track': 'Without Your Ghost',
                'timestamp': 1368089771,
                'upload_date': '20130509',
                'duration': 192,
                'tags': ['rock', 'drums', 'bass', 'world', 'punk'],
                'album': 'Duck On Cover',
                'thumbnail': 'https://usercontent.jamendo.com?type=album&id=121486&width=300&trackid=1032330',
                'view_count': int,
                'average_rating': 4,
                'license': 'by',
                'like_count': int,
            },
        }],
        'params': {
            'playlistend': 2,
        },
    }]

    def _real_extract(self, url):
        album_id = self._match_id(url)
        album = self._call_api('album', album_id)
        album_name = album.get('name')

        entries = []
        for track in (album.get('tracks') or []):
            track_id = track.get('id')
            if not track_id:
                continue
            track_id = str(track_id)
            entries.append({
                '_type': 'url_transparent',
                'url': 'https://www.jamendo.com/track/' + track_id,
                'ie_key': JamendoIE.ie_key(),
                'id': track_id,
                'album': album_name,
            })

        return self.playlist_result(
            entries, album_id, album_name,
            clean_html(try_get(album, lambda x: x['description']['en'], str)))
