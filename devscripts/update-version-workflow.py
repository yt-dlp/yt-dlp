from __future__ import unicode_literals
from datetime import datetime
# import urllib.request

# response = urllib.request.urlopen('https://blackjack4494.github.io/youtube-dlc/update/LATEST_VERSION')
# _LATEST_VERSION = response.read().decode('utf-8')

exec(compile(open('youtube_dlc/version.py').read(), 'youtube_dlc/version.py', 'exec'))
_LATEST_VERSION = locals()['__version__']

_OLD_VERSION = _LATEST_VERSION.replace('-', '.').split(".", 4)

old_ver = '.'.join(_OLD_VERSION[:3])
old_rev = _OLD_VERSION[3] if len(_OLD_VERSION) > 3 else ''

ver = datetime.now().strftime("%Y.%m.%d")
rev = str(int(old_rev or 0) + 1) if old_ver == ver else ''

version = '.'.join((ver, rev)) if rev else ver

print('::set-output name=ytdlc_version::' + version)

file_version_py = open('youtube_dlc/version.py', 'rt')
data = file_version_py.read()
data = data.replace(_LATEST_VERSION, version)
file_version_py.close()

file_version_py = open('youtube_dlc/version.py', 'wt')
file_version_py.write(data)
file_version_py.close()
