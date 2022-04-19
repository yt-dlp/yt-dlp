import itertools
import json

from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote_plus
from ..utils import (
    clean_html,
    ExtractorError,
    int_or_none,
    str_to_int,
    url_or_none,
)


class ChingariBaseIE(InfoExtractor):
    def _get_post(self, id, post_data):
        media_data = post_data['mediaLocation']
        base_url = media_data['base']
        author_data = post_data.get('authorData', {})
        song_data = post_data.get('song', {})  # revist this in future for differentiating b/w 'art' and 'author'

        formats = [{
            'format_id': frmt,
            'width': str_to_int(frmt[1:]),
            'url': base_url + frmt_path,
        } for frmt, frmt_path in media_data.get('transcoded', {}).items()]

        if media_data.get('path'):
            formats.append({
                'format_id': 'original',
                'format_note': 'Direct video.',
                'url': base_url + '/apipublic' + media_data['path'],
                'quality': 10,
            })
        self._sort_formats(formats)
        timestamp = str_to_int(post_data.get('created_at'))
        if timestamp:
            timestamp = int_or_none(timestamp, 1000)

        thumbnail, uploader_url = None, None
        if media_data.get('thumbnail'):
            thumbnail = base_url + media_data.get('thumbnail')
        if author_data.get('username'):
            uploader_url = 'https://chingari.io/' + author_data.get('username')

        return {
            'id': id,
            'extractor_key': ChingariIE.ie_key(),
            'extractor': 'Chingari',
            'title': compat_urllib_parse_unquote_plus(clean_html(post_data.get('caption'))),
            'description': compat_urllib_parse_unquote_plus(clean_html(post_data.get('caption'))),
            'duration': media_data.get('duration'),
            'thumbnail': url_or_none(thumbnail),
            'like_count': post_data.get('likeCount'),
            'view_count': post_data.get('viewsCount'),
            'comment_count': post_data.get('commentCount'),
            'repost_count': post_data.get('shareCount'),
            'timestamp': timestamp,
            'uploader_id': post_data.get('userId') or author_data.get('_id'),
            'uploader': author_data.get('name'),
            'uploader_url': url_or_none(uploader_url),
            'track': song_data.get('title'),
            'artist': song_data.get('author'),
            'formats': formats,
        }


class ChingariIE(ChingariBaseIE):
    _VALID_URL = r'https?://(?:www\.)?chingari\.io/share/post\?id=(?P<id>[^&/#?]+)'
    _TESTS = [{
        'url': 'https://chingari.io/share/post?id=612f8f4ce1dc57090e8a7beb',
        'info_dict': {
            'id': '612f8f4ce1dc57090e8a7beb',
            'ext': 'mp4',
            'title': 'Happy birthday Srila Prabhupada',
            'description': 'md5:c7080ebfdfeb06016e638c286d6bc3fa',
            'duration': 0,
            'thumbnail': 'https://media.chingari.io/uploads/c41d30e2-06b6-4e3b-9b4b-edbb929cec06-1630506826911/thumbnail/198f993f-ce87-4623-82c6-cd071bd6d4f4-1630506828016.jpg',
            'like_count': int,
            'view_count': int,
            'comment_count': int,
            'repost_count': int,
            'timestamp': 1630506828,
            'upload_date': '20210901',
            'uploader_id': '5f0403982c8bd344f4813f8c',
            'uploader': 'ISKCON,Inc.',
            'uploader_url': 'https://chingari.io/iskcon,inc',
            'track': None,
            'artist': None,
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        post_json = self._download_json(f'https://api.chingari.io/post/post_details/{id}', id)
        if post_json['code'] != 200:
            raise ExtractorError(post_json['message'], expected=True)
        post_data = post_json['data']
        return self._get_post(id, post_data)


class ChingariUserIE(ChingariBaseIE):
    _VALID_URL = r'https?://(?:www\.)?chingari\.io/(?!share/post)(?P<id>[^/?]+)'
    _TESTS = [{
        'url': 'https://chingari.io/dada1023',
        'info_dict': {
            'id': 'dada1023',
        },
        'params': {'playlistend': 3},
        'playlist': [{
            'url': 'https://chingari.io/share/post?id=614781f3ade60b3a0bfff42a',
            'info_dict': {
                'id': '614781f3ade60b3a0bfff42a',
                'ext': 'mp4',
                'title': '#chingaribappa ',
                'description': 'md5:d1df21d84088770468fa63afe3b17857',
                'duration': 7,
                'thumbnail': 'https://media.chingari.io/uploads/346d86d4-abb2-474e-a164-ffccf2bbcb72-1632076273717/thumbnail/b0b3aac2-2b86-4dd1-909d-9ed6e57cf77c-1632076275552.jpg',
                'like_count': int,
                'view_count': int,
                'comment_count': int,
                'repost_count': int,
                'timestamp': 1632076275,
                'upload_date': '20210919',
                'uploader_id': '5efc4b12cca35c3d1794c2d3',
                'uploader': 'dada (girish) dhawale',
                'uploader_url': 'https://chingari.io/dada1023',
                'track': None,
                'artist': None
            },
            'params': {'skip_download': True}
        }, {
            'url': 'https://chingari.io/share/post?id=6146b132bcbf860959e12cba',
            'info_dict': {
                'id': '6146b132bcbf860959e12cba',
                'ext': 'mp4',
                'title': 'Tactor harvesting',
                'description': 'md5:8403f12dce68828b77ecee7eb7e887b7',
                'duration': 59.3,
                'thumbnail': 'https://media.chingari.io/uploads/b353ca70-7a87-400d-93a6-fa561afaec86-1632022814584/thumbnail/c09302e3-2043-41b1-a2fe-77d97e5bd676-1632022834260.jpg',
                'like_count': int,
                'view_count': int,
                'comment_count': int,
                'repost_count': int,
                'timestamp': 1632022834,
                'upload_date': '20210919',
                'uploader_id': '5efc4b12cca35c3d1794c2d3',
                'uploader': 'dada (girish) dhawale',
                'uploader_url': 'https://chingari.io/dada1023',
                'track': None,
                'artist': None
            },
            'params': {'skip_download': True}
        }, {
            'url': 'https://chingari.io/share/post?id=6145651b74cb030a64c40b82',
            'info_dict': {
                'id': '6145651b74cb030a64c40b82',
                'ext': 'mp4',
                'title': '#odiabhajan ',
                'description': 'md5:687ea36835b9276cf2af90f25e7654cb',
                'duration': 56.67,
                'thumbnail': 'https://media.chingari.io/uploads/6cbf216b-babc-4cce-87fe-ceaac8d706ac-1631937782708/thumbnail/8855754f-6669-48ce-b269-8cc0699ed6da-1631937819522.jpg',
                'like_count': int,
                'view_count': int,
                'comment_count': int,
                'repost_count': int,
                'timestamp': 1631937819,
                'upload_date': '20210918',
                'uploader_id': '5efc4b12cca35c3d1794c2d3',
                'uploader': 'dada (girish) dhawale',
                'uploader_url': 'https://chingari.io/dada1023',
                'track': None,
                'artist': None
            },
            'params': {'skip_download': True}
        }],
    }, {
        'url': 'https://chingari.io/iskcon%2Cinc',
        'playlist_mincount': 1025,
        'info_dict': {
            'id': 'iskcon%2Cinc',
        },
    }]

    def _entries(self, id):
        skip = 0
        has_more = True
        for page in itertools.count():
            posts = self._download_json('https://api.chingari.io/users/getPosts', id,
                                        data=json.dumps({'userId': id, 'ownerId': id, 'skip': skip, 'limit': 20}).encode(),
                                        headers={'content-type': 'application/json;charset=UTF-8'},
                                        note='Downloading page %s' % page)
            for post in posts.get('data', []):
                post_data = post['post']
                yield self._get_post(post_data['_id'], post_data)
            skip += 20
            has_more = posts['hasMoreData']
            if not has_more:
                break

    def _real_extract(self, url):
        alt_id = self._match_id(url)
        post_json = self._download_json(f'https://api.chingari.io/user/{alt_id}', alt_id)
        if post_json['code'] != 200:
            raise ExtractorError(post_json['message'], expected=True)
        id = post_json['data']['_id']
        return self.playlist_result(self._entries(id), playlist_id=alt_id)
