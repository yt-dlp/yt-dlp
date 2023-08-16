"""Deprecated - New code should avoid these"""
import warnings

from .compat_utils import passthrough_module

# XXX: Implement this the same way as other DeprecationWarnings without circular import
passthrough_module(__name__, '.._legacy', callback=lambda attr: warnings.warn(
    DeprecationWarning(f'{__name__}.{attr} is deprecated'), stacklevel=6))
del passthrough_module

import base64
import urllib.error
import urllib.parse

compat_str = str

compat_b64decode = base64.b64decode

compat_urlparse = urllib.parse
compat_parse_qs = urllib.parse.parse_qs
compat_urllib_parse_unquote = urllib.parse.unquote
compat_urllib_parse_urlencode = urllib.parse.urlencode
compat_urllib_parse_urlparse = urllib.parse.urlparse
