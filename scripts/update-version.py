# Unused

from __future__ import unicode_literals
from datetime import datetime
import urllib.request

response = urllib.request.urlopen('https://blackjack4494.github.io/youtube-dlc/update/LATEST_VERSION')

_LATEST_VERSION = response.read().decode('utf-8')

_OLD_VERSION = _LATEST_VERSION.rsplit("-", 1)

if len(_OLD_VERSION) > 0:
    old_ver = _OLD_VERSION[0]

old_rev = ''
if len(_OLD_VERSION) > 1:
    old_rev = _OLD_VERSION[1]

now = datetime.now()
# ver = f'{datetime.today():%Y.%m.%d}'
ver = now.strftime("%Y.%m.%d")
rev = ''

if old_ver == ver:
    if old_rev:
        rev = int(old_rev) + 1
    else:
        rev = 1

_SEPARATOR = '-'

version = _SEPARATOR.join(filter(None, [ver, str(rev)]))
