"""Deprecated - New code should avoid these"""

import base64
import urllib.error
import urllib.parse

compat_str = str

compat_b64decode = base64.b64decode

compat_HTTPError = urllib.error.HTTPError
compat_urlparse = urllib.parse
compat_parse_qs = urllib.parse.parse_qs
compat_urllib_parse_unquote = urllib.parse.unquote
compat_urllib_parse_urlencode = urllib.parse.urlencode
compat_urllib_parse_urlparse = urllib.parse.urlparse
