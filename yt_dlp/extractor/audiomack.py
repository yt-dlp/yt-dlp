import base64
import hashlib
import hmac
import operator
import random
import time
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    filter_dict,
    int_or_none,
    merge_dicts,
    remove_start,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class AudiomackBaseIE(InfoExtractor):
    _CONSUMER_KEY = 'bd8a07e9f23fbe9d808646b730f89b8e'

    @staticmethod
    def rfc3986(x):
        if x is None:
            return x
        return urllib.parse.quote(str(x), safe='~')

    # Source https://audiomack.com/_next/static/chunks/9129-2b9faedd600665e1.js
    # Source https://audiomack.com/_next/static/chunks/1762-d25c1c603d5950c7.js
    def sign_params(self, params, api_url):
        CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        params = {
            'oauth_version': '1.0',
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_consumer_key': 'audiomack-web',
            'oauth_timestamp': int(time.time()),
            'oauth_nonce': ''.join(random.choices(CHARS, k=32)),
            **params,
        }
        normalized_param_string = '&'.join(
            f'{self.rfc3986(key)}={self.rfc3986(value)}'
            for key, value in sorted(params.items())
        )

        params['oauth_signature'] = base64.b64encode(
            hmac.new(
                key=(self.rfc3986(self._CONSUMER_KEY) + '&').encode(),
                msg=(f'GET&{self.rfc3986(api_url)}&{self.rfc3986(normalized_param_string)}').encode(),
                digestmod=hashlib.sha1,
            ).digest(),
        ).decode()

        return params

    # Func name can be change
    @staticmethod
    def is_available(*keys, obj, types=None):
        if types is None:
            return any(obj.get(key) is not None for key in keys)

        return any(
            isinstance(obj.get(key), types)
            for key in keys
        )

    def _get_next_data(self, webpage):
        return merge_dicts(
            *traverse_obj(
                self._search_nextjs_v13_data(webpage, None),
                (..., lambda _, x: self.is_available('uploader', 'artist', obj=x, types=dict), {dict}),
            ),
        )

    def _parse_metadata(self, data, display_id=None):
        return filter_dict({
            'display_id': display_id,
            **traverse_obj(data, {
                'id': (('id', 'song_id'), {str_or_none}, any),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('image', {url_or_none}),
                'duration': ('duration', {int_or_none}),
                'timestamp': ('uploaded', {int_or_none}),
                'like_count': ('stats', 'favorites-raw', {int}),
                'view_count': ('stats', 'plays-raw', {int}),
                'repost_count': ('stats', 'reposts-raw', {int}),
                'comment_count': ('stats', 'comments', {int}),
                'release_timestamp': ('released', {int_or_none}),
                'genre': ('genre', {str}),
                'modified_timestamp': ('updated', {int_or_none}),
                'uploader': ('artist', {str}),
                'uploader_id': ('uploader', 'id', {str_or_none}),
            }),
        })

    def _get_audio_info(self, data, slug=None):
        song_id = traverse_obj(data, 'id', 'song_id')
        slug = slug or traverse_obj(data, ('links', 'self', {lambda x: urllib.parse.urlparse(x).path}, {str}))
        if not slug:
            slug = traverse_obj(data, (
                {operator.itemgetter('uploader_url_slug', 'url_slug')},
                {lambda ss: f'/{ss[0]}/song/{ss[1]}'}, {require('Song slug')},
            ))

        api_url = f'https://api.audiomack.com/v1/music/play/{song_id}'
        audio_url = traverse_obj(
            self._download_json(
                api_url, song_id,
                note='Fetching audio url',
                query=self.sign_params({
                    'environment': 'desktop-web',
                    'hq': 'true',
                    'section': f'/{remove_start(slug, "/")}',
                }, api_url),
                errnote=False, fatal=False,
            ), ('signedUrl', {url_or_none}),
        )

        if not audio_url:
            raise ExtractorError('Unable to extract audio url')

        return {
            'url': audio_url,
            'ext': determine_ext(audio_url, default_ext='mp3'),
        }


class AudiomackIE(AudiomackBaseIE):
    _VALID_URL = r'https?://(?:www\.)?audiomack\.com/(?:song/|(?=.+/song/))(?P<id>[\w/-]+)'
    IE_NAME = 'audiomack'
    _TESTS = [
        # hosted on audiomack
        {
            'url': 'https://www.audiomack.com/roosh-williams/song/extraordinary',
            'info_dict':
            {
                'id': '310086',
                'display_id': 'extraordinary',
                'ext': 'mp3',
                'title': 'Extraordinary',
                'uploader': 'Roosh Williams',
                'description': 'md5:e1c9d4cdcd65e24d2fa9bd9e2ad6f8d1',
                'uploader_id': '8694',
                'comment_count': int,
                'view_count': int,
                'like_count': int,
                'repost_count': int,
                'duration': 249,
                'thumbnail': 'https://i.audiomack.com/roosh-williams/b5a6e052f2.webp',
                'genres': ['rap'],
                'timestamp': 1414075043,
                'upload_date': '20141023',
                'release_timestamp': 1414075048,
                'release_date': '20141023',
                'modified_timestamp': 1759650163,
                'modified_date': '20251005',
            },
        },
        # audiomack wrapper around soundcloud song
        # Needs new test URL.
        {
            'add_ie': ['Soundcloud'],
            'url': 'https://www.audiomack.com/song/hip-hop-daily/black-mamba-freestyle',
            'info_dict': {
                'id': '258901379',
                'ext': 'mp3',
                'description': 'mamba day freestyle for the legend Kobe Bryant ',
                'title': 'Black Mamba Freestyle [Prod. By Danny Wolf]',
                'uploader': 'ILOVEMAKONNEN',
                'upload_date': '20160414',
            },
            'skip': 'Song has been removed from the site',
        },
    ]

    def _real_extract(self, url):
        slug = self._match_id(url)
        song_id = slug.split('/')[-1]

        data = self._get_next_data(self._download_webpage(url, song_id))

        return {
            'display_id': song_id,
            **self._parse_metadata(data, song_id),
            **self._get_audio_info(data),
        }


class AudiomackAlbumIE(AudiomackBaseIE):
    _VALID_URL = r'https?://(?:www\.)?audiomack\.com/(?!.+/song.)(?P<id>[\w/-]+)'
    IE_NAME = 'audiomack:album'
    _TESTS = [
        # Standard album playlist
        {
            'url': 'https://www.audiomack.com/album/flytunezcom/tha-tour-part-2-mixtape',
            'playlist_count': 11,
            'info_dict':
            {
                'id': '812251',
                'title': 'Tha Tour: Part 2 (Official Mixtape)',
            },
            'skip': 'Album removed',
        },
        # Album playlist ripped from fakeshoredrive with no metadata
        {
            'url': 'https://www.audiomack.com/album/fakeshoredrive/ppp-pistol-p-project',
            'info_dict': {
                'title': 'PPP (Pistol P Project)',
                'id': '837572',
                'display_id': 'ppp-pistol-p-project',
                'description': 'www.fakeshoredrive.com',
                'uploader': 'Lil Herb a.k.a. G Herbo',
                'uploader_id': '2931',
                'comment_count': int,
                'view_count': int,
                'like_count': int,
                'repost_count': int,
                'thumbnail': 'https://i.audiomack.com/fakeshoredrive/cc71d55202.webp',
                'genres': ['rap'],
                'timestamp': 1419630579,
                'upload_date': '20141226',
                'release_timestamp': 1419630545,
                'release_date': '20141226',
                'modified_timestamp': 1759648996,
                'modified_date': '20251005',
            },
            'playlist': [{
                'info_dict': {
                    'id': '837576',
                    'ext': 'm4a',
                    'title': '8. Real (prod by SYK SENSE  )',
                    'uploader': 'G HERBO',
                    'duration': 157,
                    'genres': ['rap'],
                    'release_timestamp': 1419630545,
                    'release_date': '20141226',
                },
            }, {
                'info_dict': {
                    'id': '837580',
                    'ext': 'm4a',
                    'title': '10. 4 Minutes Of Hell Part 4 (prod by DY OF 808 MAFIA)',
                    'uploader': 'G HERBO',
                    'duration': 283,
                    'genres': ['rap'],
                    'release_timestamp': 1419630545,
                    'release_date': '20141226',
                },
            }],
        },
        {
            'url': 'https://audiomack.com/geo-charts/playlist/india',
            'playlist_count': 100,
            'info_dict': {
                'id': '25893804',
                'display_id': 'india',
                'title': 'Weekly 100: India',
                'description': '',
                'comment_count': int,
                'view_count': int,
                'like_count': int,
                'repost_count': int,
                'thumbnail': 'https://i.audiomack.com/india/3bd53510a6.webp',
                'genres': ['other'],
                'modified_timestamp': 1782316654,
                'modified_date': '20260624',
            },
        },
    ]

    def _real_extract(self, url):
        slug = self._match_id(url)
        playlist_id = slug.split('/')[-1]

        data = self._get_next_data(self._download_webpage(url, playlist_id))

        def entries(data):
            for track in traverse_obj(data, ('tracks', lambda _, x: self.is_available('song_id', 'id', obj=x))) or []:
                yield {
                    **self._parse_metadata(track),
                    **self._get_audio_info(track),
                }

        return self.playlist_result(entries(data), **self._parse_metadata(data, playlist_id))
