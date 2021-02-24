from __future__ import unicode_literals
from datetime import datetime
# import urllib.request

# response = urllib.request.urlopen('https://blackjack4494.github.io/youtube-dlc/update/LATEST_VERSION')
# old_version = response.read().decode('utf-8')

exec(compile(open('yt_dlp/version.py').read(), 'yt_dlp/version.py', 'exec'))
old_version = locals()['__version__']

old_version_list = old_version.split(".", 4)

old_ver = '.'.join(old_version_list[:3])
old_rev = old_version_list[3] if len(old_version_list) > 3 else ''

ver = datetime.utcnow().strftime("%Y.%m.%d")
rev = str(int(old_rev or 0) + 1) if old_ver == ver else ''

VERSION = '.'.join((ver, rev)) if rev else ver
# VERSION_LIST = [(int(v) for v in ver.split(".") + [rev or 0])]

print('::set-output name=ytdlp_version::' + VERSION)

file_version_py = open('yt_dlp/version.py', 'rt')
data = file_version_py.read()
data = data.replace(old_version, VERSION)
file_version_py.close()

file_version_py = open('yt_dlp/version.py', 'wt')
file_version_py.write(data)
file_version_py.close()
