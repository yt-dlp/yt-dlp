# Unused

#!/usr/bin/env python
from __future__ import unicode_literals

import io
import json
import mimetypes
import netrc
import optparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.compat import (
    compat_basestring,
    compat_getpass,
    compat_print,
    compat_urllib_request,
)
from yt_dlp.utils import (
    make_HTTPS_handler,
    sanitized_Request,
)


class GitHubReleaser(object):
    _API_URL = 'https://api.github.com/repos/ytdl-org/youtube-dl/releases'
    _UPLOADS_URL = 'https://uploads.github.com/repos/ytdl-org/youtube-dl/releases/%s/assets?name=%s'
    _NETRC_MACHINE = 'github.com'

    def __init__(self, debuglevel=0):
        self._init_github_account()
        https_handler = make_HTTPS_handler({}, debuglevel=debuglevel)
        self._opener = compat_urllib_request.build_opener(https_handler)

    def _init_github_account(self):
        try:
            info = netrc.netrc().authenticators(self._NETRC_MACHINE)
            if info is not None:
                self._token = info[2]
                compat_print('Using GitHub credentials found in .netrc...')
                return
            else:
                compat_print('No GitHub credentials found in .netrc')
        except (IOError, netrc.NetrcParseError):
            compat_print('Unable to parse .netrc')
        self._token = compat_getpass(
            'Type your GitHub PAT (personal access token) and press [Return]: ')

    def _call(self, req):
        if isinstance(req, compat_basestring):
            req = sanitized_Request(req)
        req.add_header('Authorization', 'token %s' % self._token)
        response = self._opener.open(req).read().decode('utf-8')
        return json.loads(response)

    def list_releases(self):
        return self._call(self._API_URL)

    def create_release(self, tag_name, name=None, body='', draft=False, prerelease=False):
        data = {
            'tag_name': tag_name,
            'target_commitish': 'master',
            'name': name,
            'body': body,
            'draft': draft,
            'prerelease': prerelease,
        }
        req = sanitized_Request(self._API_URL, json.dumps(data).encode('utf-8'))
        return self._call(req)

    def create_asset(self, release_id, asset):
        asset_name = os.path.basename(asset)
        url = self._UPLOADS_URL % (release_id, asset_name)
        # Our files are small enough to be loaded directly into memory.
        data = open(asset, 'rb').read()
        req = sanitized_Request(url, data)
        mime_type, _ = mimetypes.guess_type(asset_name)
        req.add_header('Content-Type', mime_type or 'application/octet-stream')
        return self._call(req)


def main():
    parser = optparse.OptionParser(usage='%prog CHANGELOG VERSION BUILDPATH')
    options, args = parser.parse_args()
    if len(args) != 3:
        parser.error('Expected a version and a build directory')

    changelog_file, version, build_path = args

    with io.open(changelog_file, encoding='utf-8') as inf:
        changelog = inf.read()

    mobj = re.search(r'(?s)version %s\n{2}(.+?)\n{3}' % version, changelog)
    body = mobj.group(1) if mobj else ''

    releaser = GitHubReleaser()

    new_release = releaser.create_release(
        version, name='yt-dlp %s' % version, body=body)
    release_id = new_release['id']

    for asset in os.listdir(build_path):
        compat_print('Uploading %s...' % asset)
        releaser.create_asset(release_id, os.path.join(build_path, asset))


if __name__ == '__main__':
    main()
