# coding: utf-8
from __future__ import unicode_literals

import datetime
import re

from urllib.parse import urlencode


try:
    from .instances import instances
except ImportError:
    instances = ()

from ..common import SelfHostedInfoExtractor
from ...compat import compat_str
from ...utils import (
    get_first_group,
    int_or_none,
    parse_resolution,
    str_or_none,
    traverse_obj,
    try_get,
    unified_timestamp,
    url_or_none,
    urljoin,
    ExtractorError,
)


known_valid_instances = set()


class PeerTubeBaseIE(SelfHostedInfoExtractor):
    _UUID_RE = r'[\da-zA-Z]{22}|[\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}'
    _SH_VALID_CONTENT_STRINGS = (
        '<title>PeerTube<',
        'There will be other non JS-based clients to access PeerTube',
        '>There are other non JS-based unofficial clients to access PeerTube',
        '>We are sorry but it seems that PeerTube is not compatible with your web browser.<',
        '<meta property="og:platform" content="PeerTube"',
    )
    _API_BASE = 'https://%s/api/v1/%s/%s/%s'
    _NETRC_MACHINE = 'peertube'
    _LOGIN_INFO = None

    _HOSTNAME_GROUPS = ('host', 'host_2')
    _INSTANCE_LIST = instances
    _DYNAMIC_INSTANCE_LIST = known_valid_instances
    _NODEINFO_SOFTWARE = ('peertube', )
    _SOFTWARE_NAME = 'PeerTube'

    def _login(self):
        if self._LOGIN_INFO:
            ts = datetime.datetime.now().timestamp()
            if self._LOGIN_INFO['expires_on'] >= ts + 5:
                return True

        username, password = self._get_login_info()
        if not username:
            return None

        # the instance domain (the one where user has an account) must be separated from the user e-mail
        mobj = re.match(r'^(?P<username>[^@]+(?:@[^@]+)?)@(?P<instance>.+)$', username)
        if not mobj:
            self.report_warning(
                'Invalid login format - must be in format [username or email]@[instance]')
        username, instance = mobj.group('username', 'instance')

        oauth_keys = self._downloader.cache.load('peertube-oauth', instance)
        if not oauth_keys:
            oauth_keys = self._download_json(f'https://{instance}/api/v1/oauth-clients/local', instance, 'Downloading OAuth keys')
            self._downloader.cache.store('peertube-oauth', instance, oauth_keys)
        client_id, client_secret = oauth_keys['client_id'], oauth_keys['client_secret']

        auth_res = self._download_json(f'https://{instance}/api/v1/users/token', instance, 'Logging in', data=bytes(urlencode({
            'client_id': client_id,
            'client_secret': client_secret,
            'response_type': 'code',
            'grant_type': 'password',
            'scope': 'user',
            'username': username,
            'password': password,
        }).encode('utf-8')))

        ts = datetime.datetime.now().timestamp()
        auth_res['instance'] = instance
        auth_res['expires_on'] = ts + auth_res['expires_in']
        auth_res['refresh_token_expires_on'] = ts + auth_res['refresh_token_expires_in']
        # not using self to set the details to expose it to all peertube extractors
        PeerTubeBaseIE._LOGIN_INFO = auth_res

    @classmethod
    def _match_id_and_host(cls, url):
        mobj = cls._match_valid_url(url)
        host = get_first_group(mobj, 'host', 'host_2')
        video_id = mobj.group('id')
        return host, video_id

    @staticmethod
    def _is_probe_enabled(ydl):
        return ydl.params.get('check_peertube_instance', False)

    def _call_api(self, host, resource, resource_id, path, note=None, errnote=None, fatal=True):
        return self._download_json(
            self._API_BASE % (host, resource, resource_id, path), resource_id,
            headers={
                'Authorization': f'Bearer {self._LOGIN_INFO["access_token"]}',
            } if self._LOGIN_INFO and self._LOGIN_INFO['instance'] == host else {},
            note=note, errnote=errnote, fatal=fatal)

    def _parse_video(self, video, url):
        mobj = self._match_valid_url(url)
        host = mobj.group('host') or mobj.group('host_2')
        display_id = mobj.group('id')
        info_dict = {}

        formats = []
        files = video.get('files') or []
        for playlist in (video.get('streamingPlaylists') or []):
            if not isinstance(playlist, dict):
                continue
            playlist_files = playlist.get('files')
            if not (playlist_files and isinstance(playlist_files, list)):
                continue
            files.extend(playlist_files)
        for file_ in files:
            if not isinstance(file_, dict):
                continue
            file_url = url_or_none(file_.get('fileUrl'))
            if not file_url:
                continue
            file_size = int_or_none(file_.get('size'))
            format_id = try_get(
                file_, lambda x: x['resolution']['label'], compat_str)
            f = parse_resolution(format_id)
            f.update({
                'url': file_url,
                'format_id': format_id,
                'filesize': file_size,
            })
            if format_id == '0p':
                f['vcodec'] = 'none'
            else:
                f['fps'] = int_or_none(file_.get('fps'))
            formats.append(f)
            # ytdl-patched does not support BitTorrent for now
            # if file_.get('torrentDownloadUrl'):
            #     f = f.copy()
            #     f.update({
            #         'url': file_['torrentDownloadUrl'],
            #         'ext': determine_ext(file_url),
            #         'format_id': '%s-torrent' % format_id,
            #         'protocol': 'bittorrent',
            #     })
            #     formats.append(f)
        if files:
            self._sort_formats(formats)
            info_dict['formats'] = formats
        else:
            info_dict.update({
                '_type': 'url_transparent',
                'url': 'peertube:%s:%s' % (host, video['uuid']),
                'ie_key': 'PeerTube',
            })

        def data(section, field, type_):
            return try_get(video, lambda x: x[section][field], type_)

        def account_data(field, type_):
            return data('account', field, type_)

        def channel_data(field, type_):
            return data('channel', field, type_)

        category = data('category', 'label', compat_str)
        categories = [category] if category else None

        nsfw = video.get('nsfw')
        if nsfw is bool:
            age_limit = 18 if nsfw else 0
        else:
            age_limit = None

        webpage_url = 'https://%s/videos/watch/%s' % (host, display_id)

        info_dict.update({
            'id': video['uuid'],
            'title': video['name'],
            'description': video.get('description'),
            'thumbnail': urljoin(webpage_url, video.get('thumbnailPath')),
            'timestamp': unified_timestamp(video.get('publishedAt')),
            'uploader': account_data('displayName', compat_str),
            'uploader_id': str_or_none(account_data('id', int)),
            'uploader_url': url_or_none(account_data('url', compat_str)),
            'channel': channel_data('displayName', compat_str),
            'channel_id': str_or_none(channel_data('id', int)),
            'channel_url': url_or_none(channel_data('url', compat_str)),
            'language': data('language', 'id', compat_str),
            'license': data('licence', 'label', compat_str),
            'duration': int_or_none(video.get('duration')),
            'view_count': int_or_none(video.get('views')),
            'like_count': int_or_none(video.get('likes')),
            'dislike_count': int_or_none(video.get('dislikes')),
            'age_limit': age_limit,
            'tags': try_get(video, lambda x: x['tags'], list),
            'categories': categories,
        })
        return info_dict


class PeerTubeIE(PeerTubeBaseIE):
    _VALID_URL = r'''(?x)
        (?P<prefix>peertube:)?(?:
            (?P<host>[^:]+):|
            (?P<proto>https?://)(?P<host_2>[^/]+)/(?:videos/(?:watch|embed)|api/v\d/videos|w)/
        )
        (?P<id>%s)
    ''' % PeerTubeBaseIE._UUID_RE

    _EMBED_REGEX = [r'''(?x)<iframe[^>]+\bsrc=["\'](?P<url>(?:https?:)?//{_INSTANCES_RE}/videos/embed/{cls._UUID_RE})''']
    _TESTS = [{
        'url': 'https://framatube.org/videos/watch/9c9de5e8-0a1e-484a-b099-e80766180a6d',
        'md5': '8563064d245a4be5705bddb22bb00a28',
        'info_dict': {
            'id': '9c9de5e8-0a1e-484a-b099-e80766180a6d',
            'ext': 'mp4',
            'title': 'What is PeerTube?',
            'description': 'md5:3fefb8dde2b189186ce0719fda6f7b10',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
            'timestamp': 1538391166,
            'upload_date': '20181001',
            'uploader': 'Framasoft',
            'uploader_id': '3',
            'uploader_url': 'https://framatube.org/accounts/framasoft',
            'channel': 'A propos de PeerTube',
            'channel_id': '2215',
            'channel_url': 'https://framatube.org/video-channels/joinpeertube',
            'language': 'en',
            'license': 'Attribution - Share Alike',
            'duration': 113,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'tags': ['framasoft', 'peertube'],
            'categories': ['Science & Technology'],
        }
    }, {
        'url': 'https://peertube2.cpy.re/w/122d093a-1ede-43bd-bd34-59d2931ffc5e',
        'info_dict': {
            'id': '122d093a-1ede-43bd-bd34-59d2931ffc5e',
            'ext': 'mp4',
            'title': 'E2E tests',
            'uploader_id': '37855',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
        }
    }, {
        'url': 'https://peertube2.cpy.re/w/3fbif9S3WmtTP8gGsC5HBd',
        'info_dict': {
            'id': '3fbif9S3WmtTP8gGsC5HBd',
            'ext': 'mp4',
            'title': 'E2E tests',
            'uploader_id': '37855',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
        },
    }, {
        'url': 'https://peertube2.cpy.re/api/v1/videos/3fbif9S3WmtTP8gGsC5HBd',
        'info_dict': {
            'id': '3fbif9S3WmtTP8gGsC5HBd',
            'ext': 'mp4',
            'title': 'E2E tests',
            'uploader_id': '37855',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
        },
    }, {
        # Issue #26002
        'url': 'peertube:spacepub.space:d8943b2d-8280-497b-85ec-bc282ec2afdc',
        'info_dict': {
            'id': 'd8943b2d-8280-497b-85ec-bc282ec2afdc',
            'ext': 'mp4',
            'title': 'Dot matrix printer shell demo',
            'uploader_id': '3',
            'timestamp': 1587401293,
            'upload_date': '20200420',
            'uploader': 'Drew DeVault',
        }
    }, {
        # new url scheme since PeerTube 3.3
        'url': 'https://peertube2.cpy.re/w/3fbif9S3WmtTP8gGsC5HBd',
        'info_dict': {
            'id': '122d093a-1ede-43bd-bd34-59d2931ffc5e',
            'ext': 'mp4',
            'title': 'E2E tests',
            'uploader_id': '37855',
            'timestamp': 1589276219,
            'upload_date': '20200512',
            'uploader': 'chocobozzz',
        },
    }, {
        'url': 'https://peertube.debian.social/videos/watch/0b04f13d-1e18-4f1d-814e-4979aa7c9c44',
        'only_matching': True,
    }, {
        # nsfw
        'url': 'https://vod.ksite.de/videos/watch/9bb88cd3-9959-46d9-9ab9-33d2bb704c39',
        'only_matching': True,
    }, {
        'url': 'https://vod.ksite.de/videos/embed/fed67262-6edb-4d1c-833b-daa9085c71d7',
        'only_matching': True,
    }, {
        'url': 'peertube:framatube.org:b37a5b9f-e6b5-415c-b700-04a5cd6ec205',
        'only_matching': True,
    }, {
        'url': 'https://peertube2.cpy.re/w/122d093a-1ede-43bd-bd34-59d2931ffc5e',
        'only_matching': True,
    }, {
        'url': 'https://peertube2.cpy.re/api/v1/videos/3fbif9S3WmtTP8gGsC5HBd',
        'only_matching': True,
    }, {
        'url': 'peertube:peertube2.cpy.re:3fbif9S3WmtTP8gGsC5HBd',
        'only_matching': True,
    }, {
        'url': 'peertube:video.blender.org:b37a5b9f-e6b5-415c-b700-04a5cd6ec205',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_peertube_url(webpage, source_url):
        mobj = re.match(
            r'https?://(?P<host>[^/]+)/(?:videos/(?:watch|embed)|w)/(?P<id>%s)'
            % PeerTubeIE._UUID_RE, source_url)
        if mobj and any(p in webpage for p in PeerTubeIE._SH_VALID_CONTENT_STRINGS):
            return 'peertube:%s:%s' % mobj.group('host', 'id')

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        embeds = tuple(super()._extract_embed_urls(url, webpage))
        if embeds:
            return embeds

        peertube_url = cls._extract_peertube_url(webpage, url)
        if peertube_url:
            return [peertube_url]

    def _get_subtitles(self, host, video_id):
        captions = self._call_api(
            host, video_id, 'captions', note='Downloading captions JSON',
            fatal=False)
        if not isinstance(captions, dict):
            return
        data = captions.get('data')
        if not isinstance(data, list):
            return
        subtitles = {}
        for e in data:
            language_id = try_get(e, lambda x: x['language']['id'], compat_str)
            caption_url = urljoin('https://%s' % host, e.get('captionPath'))
            if not caption_url:
                continue
            subtitles.setdefault(language_id or 'en', []).append({
                'url': caption_url,
            })
        return subtitles

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        host = get_first_group(mobj, 'host', 'host_2')
        video_id = mobj.group('id')

        self._login()

        if self._LOGIN_INFO and self._LOGIN_INFO['instance'] != host:
            video_search = self._call_api(
                self._LOGIN_INFO['instance'], 'search', 'videos', '?' + urlencode({
                    'search': f'https://{host}/videos/watch/{video_id}',
                }), note='Searching for remote video')
            if len(video_search) == 0:
                raise ExtractorError('Remote video not found')
            host, video_id = self._LOGIN_INFO['instance'], video_search['data'][0]['uuid']

        video = self._call_api(
            host, 'videos', video_id, '', note='Downloading video JSON')

        info_dict = self._parse_video(video, url)

        info_dict['subtitles'] = self.extract_subtitles(host, video_id)

        description = None
        if mobj.group('proto'):
            webpage = self._download_webpage(url, video_id, fatal=False) or None
            description = self._og_search_description(webpage, default=None)
        if not description:
            full_description = self._call_api(
                host, 'videos', video_id, 'description', note='Downloading description JSON',
                fatal=False)
            if isinstance(full_description, dict):
                description = str_or_none(full_description.get('description'))
        if not description:
            description = video.get('description')
        info_dict['description'] = description

        return info_dict


class PeerTubePlaylistIE(PeerTubeBaseIE):
    _VALID_URL = r'''(?x)
        (?P<prefix>peertube:playlist:)?(?:
            (?P<host>[^:]+):|
            https?://(?P<host_2>[^/]+)/(?:videos/(?:watch|embed)/playlist|api/v\d/video-playlists|w/p)/
        )
        (?P<id>%s)
    ''' % PeerTubeBaseIE._UUID_RE

    _TESTS = [{
        'url': 'https://peertube.debian.social/w/p/hFdJoTuyhNJVa1cDWd1d12',
        'info_dict': {
            'id': 'hFdJoTuyhNJVa1cDWd1d12',
            'description': 'Diversas palestras do Richard Stallman no Brasil.',
            'title': 'Richard Stallman no Brasil',
            'timestamp': 1599676222,
        },
        'playlist_mincount': 9,
    }, {
        'url': 'https://video.internet-czas-dzialac.pl/videos/watch/playlist/3c81b894-acde-4539-91a2-1748b208c14c?playlistPosition=1',
        'info_dict': {
            'id': '3c81b894-acde-4539-91a2-1748b208c14c',
            'title': 'Podcast Internet. Czas Działać!',
            'uploader_id': 3,
            'uploader': 'Internet. Czas działać!',
        },
        'playlist_mincount': 14,
    }, {
        'url': 'https://peertube2.cpy.re/w/p/hrAdcvjkMMkHJ28upnoN21',
        'only_matching': True,
    }]

    def _entries(self, url, host, display_id):
        i, ent = 0, 0
        videos = {'total': 0}
        while ent < videos['total'] or i == 0:
            videos = self._call_api(host, 'video-playlists', display_id,
                                    'videos?start=%d&count=25' % (i * 25),
                                    note=('Downloading playlist video list (page #%d)' % i))
            i += 1
            for video in videos['data']:
                ent += 1
                yield self._parse_video(video['video'], url)

    def _real_extract(self, url):
        host, display_id = self._match_id_and_host(url)

        self._login()

        playlist_data = self._call_api(host, 'video-playlists', display_id, '', 'Downloading playlist metadata')
        entries = self._entries(url, host, display_id)

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': playlist_data.get('uuid'),
            'title': playlist_data.get('displayName'),
            'description': playlist_data.get('description'),

            'channel': traverse_obj(playlist_data, ('videoChannel', 'displayName')),
            'channel_id': traverse_obj(playlist_data, ('videoChannel', 'id')),
            'channel_url': traverse_obj(playlist_data, ('videoChannel', 'url')),

            'uploader': traverse_obj(playlist_data, ('ownerAccount', 'displayName')),
            'uploader_id': traverse_obj(playlist_data, ('ownerAccount', 'displayName')),
            'uploader_url': traverse_obj(playlist_data, ('ownerAccount', 'displayName')),
        }


class PeerTubeChannelIE(PeerTubeBaseIE):
    _VALID_URL = r'''(?x)
        (?P<prefix>peertube:channel:)?(?:
            (?P<host>[^:]+):|
            https?://(?P<host_2>[^/]+)/(?:(?:api/v\d/)?video-channels|c)/
        )
        (?P<id>[^/?#]+)(?:/videos)?
    '''

    _TESTS = [{
        'url': 'https://video.internet-czas-dzialac.pl/video-channels/internet_czas_dzialac/videos',
        'info_dict': {
            'id': '2',
            'title': 'Internet. Czas działać!',
            'description': 'md5:ac35d70f6625b04b189e0b4b76e62e17',
            'uploader_id': 3,
            'uploader': 'Internet. Czas działać!',
        },
        'playlist_mincount': 14,
    }, {
        'url': 'https://framatube.org/c/bf54d359-cfad-4935-9d45-9d6be93f63e8/videos',
        'info_dict': {
            'id': 'bf54d359-cfad-4935-9d45-9d6be93f63e8',
            'timestamp': 1519917377,
            'title': 'Les vidéos de Framasoft',
        },
        'playlist_mincount': 345,
    }, {
        'url': 'https://peertube2.cpy.re/c/blender_open_movies@video.blender.org/videos',
        'info_dict': {
            'id': 'blender_open_movies@video.blender.org',
            'timestamp': 1542287810,
            'title': 'Official Blender Open Movies',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://video.internet-czas-dzialac.pl/c/internet_czas_dzialac',
        'only_matching': True,
    }]

    def _entries(self, url, host, display_id):
        i, ent = 0, 0
        videos = {'total': 0}
        while ent < videos['total'] or i == 0:
            videos = self._call_api(
                host, 'video-channels', display_id,
                'videos?start=%d&count=25&sort=publishedAt' % (i * 25),
                note=('Downloading channel video list (page #%d)' % i))
            i += 1
            for video in videos['data']:
                ent += 1
                yield self._parse_video(video, url)

    def _real_extract(self, url):
        host, display_id = self._match_id_and_host(url)

        self._login()

        channel_data = self._call_api(host, 'video-channels', display_id, '', 'Downloading channel metadata')
        entries = self._entries(url, host, display_id)

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': str_or_none(channel_data.get('id')),
            'title': channel_data.get('displayName'),
            'display_id': channel_data.get('name'),
            'description': channel_data.get('description'),

            'channel': channel_data.get('displayName'),
            'channel_id': channel_data.get('id'),
            'channel_url': channel_data.get('url'),

            'uploader': traverse_obj(channel_data, ('ownerAccount', 'displayName')),
            'uploader_id': traverse_obj(channel_data, ('ownerAccount', 'displayName')),
            'uploader_url': traverse_obj(channel_data, ('ownerAccount', 'displayName')),
        }


class PeerTubeAccountIE(PeerTubeBaseIE):
    _VALID_URL = r'''(?x)
        (?P<prefix>peertube:account:)?(?:
            (?P<host>[^:]+):|
            https?://(?P<host_2>[^/]+)/(?:(?:api/v\d/)?accounts|a)/
        )
        (?P<id>[^/?#]+)(?:/video(?:s|-channels))?
    '''

    _TESTS = [{
        'url': 'https://video.internet-czas-dzialac.pl/accounts/icd/video-channels',
        'info_dict': {
            'id': '3',
            'description': 'md5:ac35d70f6625b04b189e0b4b76e62e17',
            'uploader': 'Internet. Czas działać!',
            'title': 'Internet. Czas działać!',
            'uploader_id': 3,
        },
        'playlist_mincount': 14,
    }, {
        'url': 'https://peertube2.cpy.re/a/chocobozzz/videos',
        'info_dict': {
            'id': 'chocobozzz',
            'timestamp': 1553874564,
            'title': 'chocobozzz',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://video.internet-czas-dzialac.pl/a/icd',
        'only_matching': True,
    }]

    def _entries(self, url, host, display_id):
        i, ent = 0, 0
        videos = {'total': 0}
        while ent < videos['total'] or i == 0:
            videos = self._call_api(
                host, 'accounts', display_id,
                'videos?start=%d&count=25&sort=publishedAt' % (i * 25),
                note=('Downloading account video list (page #%d)' % i))
            i += 1
            for video in videos['data']:
                ent += 1
                yield self._parse_video(video, url)

    def _real_extract(self, url):
        host, display_id = self._match_id_and_host(url)

        self._login()

        account_data = self._call_api(host, 'accounts', display_id, '', 'Downloading account metadata')
        entries = self._entries(url, host, display_id)

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': str_or_none(account_data.get('id')),
            'title': account_data.get('displayName'),
            'display_id': account_data.get('name'),
            'description': account_data.get('description'),
            'uploader': account_data.get('displayName'),
            'uploader_id': account_data.get('id'),
            'uploader_url': account_data.get('url'),
        }
