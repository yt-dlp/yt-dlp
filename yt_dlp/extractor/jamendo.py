# coding: utf-8
from __future__ import unicode_literals

import hashlib
import random

from ..compat import compat_str
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
            # 'artist': 'Maya Filipič',
            'track': 'Stories from Emona I',
            'duration': 210,
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1217438117,
            'upload_date': '20080730',
            'license': 'by-nc-nd',
            'view_count': int,
            'like_count': int,
            'average_rating': int,
            'tags': ['piano', 'peaceful', 'newage', 'strings', 'upbeat'],
        }
    }, {
        'url': 'https://licensing.jamendo.com/en/track/1496667/energetic-rock',
        'only_matching': True,
    }]

    def _call_api(self, resource, resource_id):
        path = '/api/%ss' % resource
        rand = compat_str(random.random())
        return self._download_json(
            'https://www.jamendo.com' + path, resource_id, query={
                'id[]': resource_id,
            }, headers={
                'X-Jam-Call': '$%s*%s~' % (hashlib.sha1((path + rand).encode()).hexdigest(), rand)
            })[0]

    def _real_extract(self, url):
        track_id, display_id = self._VALID_URL_RE.match(url).groups()
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

        formats = [{
            'url': 'https://%s.jamendo.com/?trackid=%s&format=%s&from=app-97dab294'
                   % (sub_domain, track_id, format_id),
            'format_id': format_id,
            'ext': ext,
            'quality': quality,
        } for quality, (format_id, sub_domain, ext) in enumerate((
            ('mp31', 'mp3l', 'mp3'),
            ('mp32', 'mp3d', 'mp3'),
            ('ogg1', 'ogg', 'ogg'),
            ('flac', 'flac', 'flac'),
        ))]
        self._sort_formats(formats)

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
        license = track.get('licenseCC') or []

        return {
            'id': track_id,
            'display_id': display_id,
            'thumbnails': thumbnails,
            'title': title,
            'description': track.get('description'),
            'duration': int_or_none(track.get('duration')),
            # 'artist': artist_name,
            'track': track_name,
            # 'album': album.get('name'),
            'formats': formats,
            'license': '-'.join(license) if license else None,
            'timestamp': int_or_none(track.get('dateCreated')),
            'view_count': int_or_none(stats.get('listenedAll')),
            'like_count': int_or_none(stats.get('favorited')),
            'average_rating': int_or_none(stats.get('averageNote')),
            'tags': tags,
        }


class JamendoAlbumIE(JamendoIE):
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
                'title': 'Shearer - Warmachine',
                'artist': 'Shearer',
                'track': 'Warmachine',
                'timestamp': 1368089771,
                'upload_date': '20130509',
            }
        }, {
            'md5': '1f358d7b2f98edfe90fd55dac0799d50',
            'info_dict': {
                'id': '1032330',
                'ext': 'flac',
                'title': 'Shearer - Without Your Ghost',
                'artist': 'Shearer',
                'track': 'Without Your Ghost',
                'timestamp': 1368089771,
                'upload_date': '20130509',
            }
        }],
        'params': {
            'playlistend': 2
        }
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
            track_id = compat_str(track_id)
            entries.append({
                '_type': 'url_transparent',
                'url': 'https://www.jamendo.com/track/' + track_id,
                'ie_key': JamendoIE.ie_key(),
                'id': track_id,
                'album': album_name,
            })

        return self.playlist_result(
            entries, album_id, album_name,
            clean_html(try_get(album, lambda x: x['description']['en'], compat_str)))
