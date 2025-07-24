import base64
import itertools
import urllib.parse

from .common import InfoExtractor
from ..compat import compat_ord
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
    strip_or_none,
    try_get,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class MixcloudBaseIE(InfoExtractor):
    def _call_api(self, object_type, object_fields, display_id, username, slug=None):
        lookup_key = object_type + 'Lookup'
        return self._download_json(
            'https://app.mixcloud.com/graphql', display_id, query={
                'query': '''{
  %s(lookup: {username: "%s"%s}) {
    %s
  }
}''' % (lookup_key, username, f', slug: "{slug}"' if slug else '', object_fields),  # noqa: UP031
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
            'uploader': 'dholbach',
            'uploader_id': 'dholbach',
            'thumbnail': r're:https?://.*\.jpg',
            'view_count': int,
            'timestamp': 1321359578,
            'upload_date': '20111115',
            'uploader_url': 'https://www.mixcloud.com/dholbach/',
            'artist': 'Submorphics & Chino , Telekinesis, Porter Robinson, Enei, Breakage ft Jess Mills',
            'duration': 3723,
            'tags': ['liquid drum and bass', 'drum and bass'],
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
            'artists': list,
        },
        'params': {'skip_download': 'm3u8'},
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
            'uploader_url': 'https://www.mixcloud.com/gillespeterson/',
            'duration': 2992,
            'tags': ['jazz', 'soul', 'world music', 'funk'],
            'comment_count': int,
            'repost_count': int,
            'like_count': int,
        },
        'params': {'skip_download': '404 playback error on site'},
    }, {
        'url': 'https://beta.mixcloud.com/RedLightRadio/nosedrip-15-red-light-radio-01-18-2016/',
        'only_matching': True,
    }]
    _DECRYPTION_KEY = 'IFYOUWANTTHEARTISTSTOGETPAIDDONOTDOWNLOADFROMMIXCLOUD'

    @staticmethod
    def _decrypt_xor_cipher(key, ciphertext):
        """Encrypt/Decrypt XOR cipher. Both ways are possible because it's XOR."""
        return ''.join([
            chr(compat_ord(ch) ^ compat_ord(k))
            for ch, k in zip(ciphertext, itertools.cycle(key))])

    def _real_extract(self, url):
        username, slug = self._match_valid_url(url).groups()
        username, slug = urllib.parse.unquote(username), urllib.parse.unquote(slug)
        track_id = f'{username}_{slug}'

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
    }
    restrictedReason
    id''', track_id, username, slug)

        if not cloudcast:
            raise ExtractorError('Track not found', expected=True)

        reason = cloudcast.get('restrictedReason')
        if reason == 'tracklist':
            raise ExtractorError('Track unavailable in your country due to licensing restrictions', expected=True)
        elif reason == 'repeat_play':
            raise ExtractorError('You have reached your play limit for this track', expected=True)
        elif reason:
            raise ExtractorError('Track is restricted', expected=True)

        stream_info = cloudcast['streamInfo']
        formats = []

        for url_key in ('url', 'hlsUrl', 'dashUrl'):
            format_url = stream_info.get(url_key)
            if not format_url:
                continue
            decrypted = self._decrypt_xor_cipher(
                self._DECRYPTION_KEY, base64.b64decode(format_url))
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
                    'vcodec': 'none',
                    'downloader_options': {
                        # Mixcloud starts throttling at >~5M
                        'http_chunk_size': 5242880,
                    },
                })

        if not formats and cloudcast.get('isExclusive'):
            self.raise_login_required(metadata_available=True)

        comments = []
        for node in traverse_obj(cloudcast, ('comments', 'edges', ..., 'node', {dict})):
            text = strip_or_none(node.get('comment'))
            if not text:
                continue
            comments.append({
                'text': text,
                **traverse_obj(node, {
                    'author': ('user', 'displayName', {str}),
                    'author_id': ('user', 'username', {str}),
                    'timestamp': ('created', {parse_iso8601}),
                }),
            })

        return {
            'id': track_id,
            'formats': formats,
            'comments': comments,
            **traverse_obj(cloudcast, {
                'title': ('name', {str}),
                'description': ('description', {str}),
                'thumbnail': ('picture', 'url', {url_or_none}),
                'timestamp': ('publishDate', {parse_iso8601}),
                'duration': ('audioLength', {int_or_none}),
                'uploader': ('owner', 'displayName', {str}),
                'uploader_id': ('owner', 'username', {str}),
                'uploader_url': ('owner', 'url', {url_or_none}),
                'view_count': ('plays', {int_or_none}),
                'like_count': ('favorites', 'totalCount', {int_or_none}),
                'repost_count': ('reposts', 'totalCount', {int_or_none}),
                'comment_count': ('comments', 'totalCount', {int_or_none}),
                'tags': ('tags', ..., 'tag', 'name', {str}, filter, all, filter),
                'artists': ('featuringArtistList', ..., {str}, filter, all, filter),
            }),
        }


class MixcloudPlaylistBaseIE(MixcloudBaseIE):
    def _get_cloudcast(self, node):
        return node

    def _get_playlist_title(self, title, slug):
        return title

    def _real_extract(self, url):
        username, slug = self._match_valid_url(url).groups()
        username = urllib.parse.unquote(username)
        if not slug:
            slug = 'uploads'
        else:
            slug = urllib.parse.unquote(slug)
        playlist_id = f'{username}_{slug}'

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
    }''' % (self._TITLE_KEY, self._DESCRIPTION_KEY, playlist_type, list_filter, self._NODE_TEMPLATE),  # noqa: UP031
                playlist_id, username, slug if is_playlist_type else None)

            items = playlist.get(playlist_type) or {}
            for edge in items.get('edges', []):
                cloudcast = self._get_cloudcast(edge.get('node') or {})
                cloudcast_url = cloudcast.get('url')
                if not cloudcast_url:
                    continue
                item_slug = try_get(cloudcast, lambda x: x['slug'], str)
                owner_username = try_get(cloudcast, lambda x: x['owner']['username'], str)
                video_id = f'{owner_username}_{item_slug}' if item_slug and owner_username else None
                entries.append(self.url_result(
                    cloudcast_url, MixcloudIE.ie_key(), video_id))

            page_info = items['pageInfo']
            has_next_page = page_info['hasNextPage']
            list_filter = ', after: "{}"'.format(page_info['endCursor'])

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
            'title': 'dholbach (uploads)',
            'description': 'md5:a3f468a60ac8c3e1f8616380fc469b2b',
        },
        'playlist_mincount': 36,
    }, {
        'url': 'http://www.mixcloud.com/dholbach/uploads/',
        'info_dict': {
            'id': 'dholbach_uploads',
            'title': 'dholbach (uploads)',
            'description': 'md5:a3f468a60ac8c3e1f8616380fc469b2b',
        },
        'playlist_mincount': 36,
    }, {
        'url': 'http://www.mixcloud.com/dholbach/favorites/',
        'info_dict': {
            'id': 'dholbach_favorites',
            'title': 'dholbach (favorites)',
            'description': 'md5:a3f468a60ac8c3e1f8616380fc469b2b',
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
            'description': 'we maraud for ears',
        },
        'playlist_mincount': 267,
    }]

    _TITLE_KEY = 'displayName'
    _DESCRIPTION_KEY = 'biog'
    _ROOT_TYPE = 'user'
    _NODE_TEMPLATE = '''slug
          url
          owner { username }'''

    def _get_playlist_title(self, title, slug):
        return f'{title} ({slug})'


class MixcloudPlaylistIE(MixcloudPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?mixcloud\.com/(?P<user>[^/]+)/playlists/(?P<playlist>[^/]+)/?$'
    IE_NAME = 'mixcloud:playlist'

    _TESTS = [{
        'url': 'https://www.mixcloud.com/maxvibes/playlists/jazzcat-on-ness-radio/',
        'info_dict': {
            'id': 'maxvibes_jazzcat-on-ness-radio',
            'title': 'Ness Radio sessions',
        },
        'playlist_mincount': 58,
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
