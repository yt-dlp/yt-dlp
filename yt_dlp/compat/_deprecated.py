"""Deprecated - New code should avoid these"""

import base64
import getpass
import html
import html.parser
import http
import http.client
import http.cookiejar
import http.cookies
import http.server
import itertools
import os
import shutil
import struct
import tokenize
import urllib

compat_b64decode = base64.b64decode
compat_chr = chr
compat_cookiejar = http.cookiejar
compat_cookiejar_Cookie = http.cookiejar.Cookie
compat_cookies_SimpleCookie = http.cookies.SimpleCookie
compat_get_terminal_size = shutil.get_terminal_size
compat_getenv = os.getenv
compat_getpass = getpass.getpass
compat_html_entities = html.entities
compat_html_entities_html5 = html.entities.html5
compat_HTMLParser = html.parser.HTMLParser
compat_http_client = http.client
compat_http_server = http.server
compat_HTTPError = urllib.error.HTTPError
compat_itertools_count = itertools.count
compat_parse_qs = urllib.parse.parse_qs
compat_str = str
compat_struct_pack = struct.pack
compat_struct_unpack = struct.unpack
compat_tokenize_tokenize = tokenize.tokenize
compat_urllib_error = urllib.error
compat_urllib_parse_unquote = urllib.parse.unquote
compat_urllib_parse_unquote_plus = urllib.parse.unquote_plus
compat_urllib_parse_urlencode = urllib.parse.urlencode
compat_urllib_parse_urlparse = urllib.parse.urlparse
compat_urllib_request = urllib.request
compat_urlparse = compat_urllib_parse = urllib.parse


def compat_setenv(key, value, env=os.environ):
    env[key] = value


__all__ = [x for x in globals() if x.startswith('compat_')]
