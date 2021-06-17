#!/usr/bin/env python3
from __future__ import unicode_literals

import json
import sys
import hashlib
import os.path


if len(sys.argv) <= 1:
    print('Specify the version number as parameter')
    sys.exit()
version = sys.argv[1]

with open('update/LATEST_VERSION', 'w') as f:
    f.write(version)

versions_info = json.load(open('update/versions.json'))
if 'signature' in versions_info:
    del versions_info['signature']

new_version = {}

filenames = {
    'bin': 'yt-dlp',
    'exe': 'yt-dlp.exe',
    'tar': 'yt-dlp-%s.tar.gz' % version}
build_dir = os.path.join('..', '..', 'build', version)
for key, filename in filenames.items():
    url = 'https://yt-dl.org/downloads/%s/%s' % (version, filename)
    fn = os.path.join(build_dir, filename)
    with open(fn, 'rb') as f:
        data = f.read()
    if not data:
        raise ValueError('File %s is empty!' % fn)
    sha256sum = hashlib.sha256(data).hexdigest()
    new_version[key] = (url, sha256sum)

versions_info['versions'][version] = new_version
versions_info['latest'] = version

with open('update/versions.json', 'w') as jsonf:
    json.dump(versions_info, jsonf, indent=4, sort_keys=True)
