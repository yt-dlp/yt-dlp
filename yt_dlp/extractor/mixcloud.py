from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..compat import (
    compat_b64decode,
    compat_chr,
    compat_ord,
    compat_str,
    compat_urllib_parse_unquote,
    compat_zip
)
from ..utils import (
    int_or_none,
    parse_iso8601,
    strip_or_none,
    try_get,
)


class MixcloudBaseIE(InfoExtractor):
    def _call_api(self, object_type, object_fields, display_id, username, slug=None):
        lookup_key = object_type + 'Lookup'
        return self._download_json(
            'https://www.mixcloud.com/graphql', display_id, query={
                'query': '''{
  %s(lookup: {username: "%s"%s}) {
    %s
  }
}''' % (lookup_key, username, ', slug: "%s"' % slug if slug else '', object_fields)
            })['data'][lookup_key]


class MixcloudIE(MixcloudBaseIE):
    _VALID_URL = r'https?://(?:(?:www|beta|m)\.)?mixcloud\.com/([^/]+)/(?!stream|uploads|favorites|listens|playlists)([^/]+)'
    IE_NAME = 'mixcloud'

    _TESTS = [{
        'url': 'http://www.mixcloud.com/dholbach/cryptkeeper/',
        'info_dict': {
            'id': 'dholbach_cryptkeeper',
            'ext': 'm4a',
            'title': 'Cryptkeeper',
            'description': 'After quite a long silence from myself, finally another Drum\'n\'Bass mix with my favourite current dance floor bangers.',
            'uploader': 'Daniel Holbach',
            'uploader_id': 'dholbach',
            'thumbnail': r're:https?://.*\.jpg',
            'view_count': int,
            'timestamp': 1321359578,
            'upload_date': '20111115',
        },
    }, {
        'url': 'http://www.mixcloud.com/gillespeterson/caribou-7-inch-vinyl-mix-chat/',
        'info_dict': {
            'id': 'gillespeterson_caribou-7-inch-vinyl-mix-chat',
            'ext': 'mp3',
            'title': 'Caribou 7 inch Vinyl Mix & Chat',
            'description': 'md5:2b8aec6adce69f9d41724647c65875e8',
            'uploader': 'Gilles Peterson Worldwide',
            'uploader_id': 'gillespeterson',
            'thumbnail': 're:https?://.*',
            'view_count': int,
            'timestamp': 1422987057,
            'upload_date': '20150203',
        },
    }, {
        'url': 'https://beta.mixcloud.com/RedLightRadio/nosedrip-15-red-light-radio-01-18-2016/',
        'only_matching': True,
    }]
    _DECRYPTION_KEY = 'IFYOUWANTTHEARTISTSTOGETPAIDDONOTDOWNLOADFROMMIXCLOUD'

    @staticmethod
    def _decrypt_xor_cipher(key, ciphertext):
        """Encrypt/Decrypt XOR cipher. Both ways are possible because it's XOR."""
        return ''.join([
            compat_chr(compat_ord(ch) ^ compat_ord(k))
            for ch, k in compat_zip(ciphertext, itertools.cycle(key))])

    def _real_extract(self, url):
        username, slug = re.match(self._VALID_URL, url).groups()
        username, slug = compat_urllib_parse_unquote(username), compat_urllib_parse_unquote(slug)
        track_id = '%s_%s' % (username, slug)

        cloudcast = self._call_api('cloudcast', '''audioLength
    comments(first: 100) {
      edges {
        node {
          comment
          created
          user {
            displayName
            username
          }
        }
      }
      totalCount
    }
    description
    favorites {
      totalCount
    }
    featuringArtistList
    isExclusive
    name
    owner {
      displayName
      url
      username
    }
    picture(width: 1024, height: 1024) {
        url
    }
    plays
    publishDate
    reposts {
      totalCount
    }
    streamInfo {
      dashUrl
      hlsUrl
      url
    }
    tags {
      tag {
        name
      }
    }''', track_id, username, slug)

        title = cloudcast['name']

        stream_info = cloudcast['streamInfo']
        formats = []

        for url_key in ('url', 'hlsUrl', 'dashUrl'):
            format_url = stream_info.get(url_key)
            if not format_url:
                continue
            decrypted = self._decrypt_xor_cipher(
                self._DECRYPTION_KEY, compat_b64decode(format_url))
            if url_key == 'hlsUrl':
                formats.extend(self._extract_m3u8_formats(
                    decrypted, track_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            elif url_key == 'dashUrl':
                formats.extend(self._extract_mpd_formats(
                    decrypted, track_id, mpd_id='dash', fatal=False))
            else:
                formats.append({
                    'format_id': 'http',
                    'url': decrypted,
                    'downloader_options': {
                        # Mixcloud starts throttling at >~5M
                        'http_chunk_size': 5242880,
                    },
                })

        if not formats and cloudcast.get('isExclusive'):
            self.raise_login_required(metadata_available=True)

        self._sort_formats(formats)

        comments = []
        for edge in (try_get(cloudcast, lambda x: x['comments']['edges']) or []):
            node = edge.get('node') or {}
            text = strip_or_none(node.get('comment'))
            if not text:
                continue
            user = node.get('user') or {}
            comments.append({
                'author': user.get('displayName'),
                'author_id': user.get('username'),
                'text': text,
                'timestamp': parse_iso8601(node.get('created')),
            })

        tags = []
        for t in cloudcast.get('tags'):
            tag = try_get(t, lambda x: x['tag']['name'], compat_str)
            if not tag:
                tags.append(tag)

        get_count = lambda x: int_or_none(try_get(cloudcast, lambda y: y[x]['totalCount']))

        owner = cloudcast.get('owner') or {}

        return {
            'id': track_id,
            'title': title,
            'formats': formats,
            'description': cloudcast.get('description'),
            'thumbnail': try_get(cloudcast, lambda x: x['picture']['url'], compat_str),
            'uploader': owner.get('displayName'),
            'timestamp': parse_iso8601(cloudcast.get('publishDate')),
            'uploader_id': owner.get('username'),
            'uploader_url': owner.get('url'),
            'duration': int_or_none(cloudcast.get('audioLength')),
            'view_count': int_or_none(cloudcast.get('plays')),
            'like_count': get_count('favorites'),
            'repost_count': get_count('reposts'),
            'comment_count': get_count('comments'),
            'comments': comments,
            'tags': tags,
            'artist': ', '.join(cloudcast.get('featuringArtistList') or []) or None,
        }


class MixcloudPlaylistBaseIE(MixcloudBaseIE):
    def _get_cloudcast(self, node):
        return node

    def _get_playlist_title(self, title, slug):
        return title

    def _real_extract(self, url):
        username, slug = re.match(self._VALID_URL, url).groups()
        username = compat_urllib_parse_unquote(username)
        if not slug:
            slug = 'uploads'
        else:
            slug = compat_urllib_parse_unquote(slug)
        playlist_id = '%s_%s' % (username, slug)

        is_playlist_type = self._ROOT_TYPE == 'playlist'
        playlist_type = 'items' if is_playlist_type else slug
        list_filter = ''

        has_next_page = True
        entries = []
        while has_next_page:
            playlist = self._call_api(
                self._ROOT_TYPE, '''%s
    %s
    %s(first: 100%s) {
      edges {
        node {
          %s
        }
      }
      pageInfo {
        endCursor
        hasNextPage
      }
    }''' % (self._TITLE_KEY, self._DESCRIPTION_KEY, playlist_type, list_filter, self._NODE_TEMPLATE),
                playlist_id, username, slug if is_playlist_type else None)

            items = playlist.get(playlist_type) or {}
            for edge in items.get('edges', []):
                cloudcast = self._get_cloudcast(edge.get('node') or {})
                cloudcast_url = cloudcast.get('url')
                if not cloudcast_url:
                    continue
                slug = try_get(cloudcast, lambda x: x['slug'], compat_str)
                owner_username = try_get(cloudcast, lambda x: x['owner']['username'], compat_str)
                video_id = '%s_%s' % (owner_username, slug) if slug and owner_username else None
                entries.append(self.url_result(
                    cloudcast_url, MixcloudIE.ie_key(), video_id))

            page_info = items['pageInfo']
            has_next_page = page_info['hasNextPage']
            list_filter = ', after: "%s"' % page_info['endCursor']

        return self.playlist_result(
            entries, playlist_id,
            self._get_playlist_title(playlist[self._TITLE_KEY], slug),
            playlist.get(self._DESCRIPTION_KEY))


class MixcloudUserIE(MixcloudPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?mixcloud\.com/(?P<id>[^/]+)/(?P<type>uploads|favorites|listens|stream)?/?$'
    IE_NAME = 'mixcloud:user'

    _TESTS = [{
        'url': 'http://www.mixcloud.com/dholbach/',
        'info_dict': {
            'id': 'dholbach_uploads',
            'title': 'Daniel Holbach (uploads)',
            'description': 'md5:b60d776f0bab534c5dabe0a34e47a789',
        },
        'playlist_mincount': 36,
    }, {
        'url': 'http://www.mixcloud.com/dholbach/uploads/',
        'info_dict': {
            'id': 'dholbach_uploads',
            'title': 'Daniel Holbach (uploads)',
            'description': 'md5:b60d776f0bab534c5dabe0a34e47a789',
        },
        'playlist_mincount': 36,
    }, {
        'url': 'http://www.mixcloud.com/dholbach/favorites/',
        'info_dict': {
            'id': 'dholbach_favorites',
            'title': 'Daniel Holbach (favorites)',
            'description': 'md5:b60d776f0bab534c5dabe0a34e47a789',
        },
        # 'params': {
        #     'playlist_items': '1-100',
        # },
        'playlist_mincount': 396,
    }, {
        'url': 'http://www.mixcloud.com/dholbach/listens/',
        'info_dict': {
            'id': 'dholbach_listens',
            'title': 'Daniel Holbach (listens)',
            'description': 'md5:b60d776f0bab534c5dabe0a34e47a789',
        },
        # 'params': {
        #     'playlist_items': '1-100',
        # },
        'playlist_mincount': 1623,
        'skip': 'Large list',
    }, {
        'url': 'https://www.mixcloud.com/FirstEar/stream/',
        'info_dict': {
            'id': 'FirstEar_stream',
            'title': 'First Ear (stream)',
            'description': 'Curators of good music\r\n\r\nfirstearmusic.com',
        },
        'playlist_mincount': 271,
    }]

    _TITLE_KEY = 'displayName'
    _DESCRIPTION_KEY = 'biog'
    _ROOT_TYPE = 'user'
    _NODE_TEMPLATE = '''slug
          url
          owner { username }'''

    def _get_playlist_title(self, title, slug):
        return '%s (%s)' % (title, slug)


class MixcloudPlaylistIE(MixcloudPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?mixcloud\.com/(?P<user>[^/]+)/playlists/(?P<playlist>[^/]+)/?$'
    IE_NAME = 'mixcloud:playlist'

    _TESTS = [{
        'url': 'https://www.mixcloud.com/maxvibes/playlists/jazzcat-on-ness-radio/',
        'info_dict': {
            'id': 'maxvibes_jazzcat-on-ness-radio',
            'title': 'Ness Radio sessions',
        },
        'playlist_mincount': 59,
    }]
    _TITLE_KEY = 'name'
    _DESCRIPTION_KEY = 'description'
    _ROOT_TYPE = 'playlist'
    _NODE_TEMPLATE = '''cloudcast {
            slug
            url
            owner { username }
          }'''

    def _get_cloudcast(self, node):
        return node.get('cloudcast') or {}
