# coding: utf-8
from __future__ import unicode_literals
import itertools
import json
import re

try:
    from .instances import instances
except ImportError:
    instances = ()

from ..common import SelfHostedInfoExtractor
from ...utils import (
    ExtractorError,
    determine_ext,
    get_first_group,
    mimetype2ext,
    smuggle_url,
    traverse_obj,
    unified_timestamp,
    unsmuggle_url,
    parse_iso8601,
)
from ...compat import compat_str


known_valid_instances = set()


class MisskeyBaseIE(SelfHostedInfoExtractor):
    _SH_VALID_CONTENT_STRINGS = (
        '<meta name="application-name" content="Misskey"',
        '<meta name="misskey:',
        '<!-- If you are reading this message... how about joining the development of Misskey? -->',
    )

    _HOSTNAME_GROUPS = ('instance', )
    _INSTANCE_LIST = instances
    _DYNAMIC_INSTANCE_LIST = known_valid_instances
    _NODEINFO_SOFTWARE = ('misskey', )
    _SOFTWARE_NAME = 'Misskey'


class MisskeyIE(MisskeyBaseIE):
    IE_NAME = 'misskey'
    _VALID_URL = r'(?P<prefix>(?:misskey|msky|msk):)?https?://(?P<instance>[a-zA-Z0-9._-]+)/notes/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'note': 'embed video',
        'url': 'https://misskey.io/notes/8pp0c7gsbm',
        'info_dict': {
            'id': '8pp0c7gsbm',
            'title': 'Misskeyダウンローダーのテストケース',
            'timestamp': 1629529895,
            'uploader': 'nao20010128',
            'uploader_id': '8pp040sbza',
            'visibility': 'public',
            'age_limit': 0,
        },
    }, {
        'note': 'another instance, and have no content (title=NA)',
        'url': 'https://misskey.dev/notes/8o0h93l7bl',
        'info_dict': {
            'id': '8o0h93l7bl',
            'title': None,
            'timestamp': 1625869866,
            'uploader': 'かに座と悪ヨメミ',
            'uploader_id': '8izhlpyfdt',
            'visibility': 'public',
            'age_limit': 0,
        },
    }, {
        'note': 'embed video with YouTube',
        'url': 'https://misskey.io/notes/8pp0di8s4t',
        # we have to port mfm-js in Node.js to mimick embed URL extraction
        # https://github.com/misskey-dev/misskey/blob/develop/src/misc/extract-url-from-mfm.ts
        # https://github.com/misskey-dev/misskey/blob/develop/src/client/ui/chat/note.vue
        # https://github.com/misskey-dev/mfm.js/blob/develop/src/internal/parser.pegjs
        'only_matching': True,
    }, {
        'note': 'no video',
        'url': 'https://misskey.io/notes/8pp04mprzx',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        instance, video_id = self._match_valid_url(url).group('instance', 'id')

        url, api_response = unsmuggle_url(url)
        if not api_response:
            api_response = self._download_json(
                'https://%s/api/notes/show' % instance, video_id,
                # building POST payload without using json module
                data=('{"noteId":"%s"}' % video_id).encode())

        title = api_response.get('text')
        timestamp = unified_timestamp(api_response.get('createdAt'))
        uploader = traverse_obj(api_response, ('user', 'name'), ('user', 'username'), expected_type=compat_str)
        uploader_id = traverse_obj(api_response, ('userId', ), ('user', 'id'), expected_type=compat_str)
        visibility = api_response.get('visibility')

        from .complement import _COMPLEMENTS
        complements = [x() for x in _COMPLEMENTS if re.match(x._INSTANCE_RE, instance)]

        files = []
        for idx, file in enumerate(api_response.get('files') or []):
            formats = []
            mimetype = file.get('type')
            if not mimetype or (not mimetype.startswith('video/') and not mimetype.startswith('audio/')):
                continue
            formats.append({
                'format_id': file.get('id'),
                'url': file.get('url'),
                'ext': mimetype2ext(mimetype) or determine_ext(file.get('name')),
                'filesize': file.get('size'),
            })

            # must be here to prevent circular import
            if complements:
                self.to_screen('%d complement(s) found, running them to get more formats' % len(complements))
                for cmpl in complements:
                    try:
                        formats.extend(cmpl._extract_formats(self, video_id, file))
                    except ExtractorError as ex:
                        self.report_warning('Error occured in complement "%s": %s' % (cmpl, ex))

            self._sort_formats(formats)

            files.append({
                'id': '%s-%d' % (video_id, idx),
                'title': title,
                'formats': formats,
                'thumbnail': file.get('thumbnailUrl'),
                'age_limit': 18 if file.get('isSensitive') else 0,
                'timestamp': parse_iso8601(file.get('createdAt')),
            })

        base = {
            'id': video_id,
            'title': title,
            'timestamp': timestamp,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'visibility': visibility,
        }
        if not files:
            raise ExtractorError('This note does not have any media file.', expected=True)
        elif len(files) == 1:
            files[0].update(base)
            return files[0]
        else:
            base.update({
                '_type': 'multi_video',
                'entries': files,
            })
            return base


class MisskeyUserIE(MisskeyBaseIE):
    IE_NAME = 'misskey:user'
    _VALID_URL = r'(?P<prefix>(?:misskey|msky|msk):)?https?://(?P<instance>[a-zA-Z0-9._-]+)/@(?P<id>[a-zA-Z0-9_-]+)(?:@(?P<instance2>[a-zA-Z0-9_.-]+))?'
    _TESTS = [{
        'note': 'refer to another instance',
        'url': 'https://misskey.io/@vitaone@misskey.dev',
        'playlist_mincount': 0,
    }, {
        'url': 'https://misskey.io/@kubaku@misskey.dev',
        'playlist_mincount': 1,
    }, {
        'url': 'https://misskey.dev/@kubaku',
        'playlist_mincount': 1,
    }]

    def _entries(self, instance, user_id):
        until_id = None
        for i in itertools.count(1):
            page = self._download_json(
                'https://%s/api/users/notes' % instance, user_id,
                note='Downloading page %d' % i, data=json.dumps({
                    'limit': 100,
                    'userId': user_id,
                    'withFiles': True,
                    **({'untilId': until_id} if until_id else {}),
                }).encode())
            yield from page
            until_id = traverse_obj(page, (-1, 'id'))
            if not until_id:
                break

    def _mapfilter_items_with_media(self, instance, entries):
        for item in entries:
            mimetypes = [x.get('type') for x in item.get('files') or [] if x]
            if any(x and (x.startswith('video/') or x.startswith('audio/')) for x in mimetypes):
                yield self.url_result(smuggle_url('https://%s/notes/%s' % (instance, item.get('id')), item))

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        instance = get_first_group(mobj, 'instance2', 'instance')
        user_handle = mobj.group('id')

        user_info = self._download_json(
            'https://%s/api/users/show' % instance, user_handle,
            note='Fetching user info',
            # building POST payload without using json module
            data=('{"username":"%s"}' % user_handle).encode())
        user_id = user_info.get('id')
        uploader = user_info.get('name')
        uploader_id = user_info.get('username')
        description = user_info.get('description')

        entries = self._mapfilter_items_with_media(instance, self._entries(instance, user_id))

        return {
            '_type': 'playlist',
            'title': 'Notes from @%s@%s' % (uploader_id, instance),
            'entries': entries,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'description': description,
        }
