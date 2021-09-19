# coding: utf-8

import asyncio
import base64
import ctypes
import getpass
import html
import html.parser
import http
import http.client
import http.cookiejar
import http.cookies
import http.server
import itertools
import optparse
import os
import re
import shlex
import shutil
import socket
import struct
import sys
import tokenize
import urllib
import xml.etree.ElementTree as etree
from subprocess import DEVNULL


# HTMLParseError has been deprecated in Python 3.3 and removed in
# Python 3.5. Introducing dummy exception for Python >3.5 for compatible
# and uniform cross-version exception handling
class compat_HTMLParseError(Exception):
    pass


def compat_ctypes_WINFUNCTYPE(*args, **kwargs):
    return ctypes.WINFUNCTYPE(*args, **kwargs)


class _TreeBuilder(etree.TreeBuilder):
    def doctype(self, name, pubid, system):
        pass


def compat_etree_fromstring(text):
    return etree.XML(text, parser=etree.XMLParser(target=_TreeBuilder()))


compat_os_name = os._name if os.name == 'java' else os.name


if compat_os_name == 'nt':
    def compat_shlex_quote(s):
        return s if re.match(r'^[-_\w./]+$', s) else '"%s"' % s.replace('"', '\\"')
else:
    from shlex import quote as compat_shlex_quote


def compat_ord(c):
    if type(c) is int:
        return c
    else:
        return ord(c)


def compat_setenv(key, value, env=os.environ):
    env[key] = value


if compat_os_name == 'nt' and sys.version_info < (3, 8):
    # os.path.realpath on Windows does not follow symbolic links
    # prior to Python 3.8 (see https://bugs.python.org/issue9949)
    def compat_realpath(path):
        while os.path.islink(path):
            path = os.path.abspath(os.readlink(path))
        return path
else:
    compat_realpath = os.path.realpath


def compat_print(s):
    assert isinstance(s, compat_str)
    print(s)


# Fix https://github.com/ytdl-org/youtube-dl/issues/4223
# See http://bugs.python.org/issue9161 for what is broken
def workaround_optparse_bug9161():
    op = optparse.OptionParser()
    og = optparse.OptionGroup(op, 'foo')
    try:
        og.add_option('-t')
    except TypeError:
        real_add_option = optparse.OptionGroup.add_option

        def _compat_add_option(self, *args, **kwargs):
            enc = lambda v: (
                v.encode('ascii', 'replace') if isinstance(v, compat_str)
                else v)
            bargs = [enc(a) for a in args]
            bkwargs = dict(
                (k, enc(v)) for k, v in kwargs.items())
            return real_add_option(self, *bargs, **bkwargs)
        optparse.OptionGroup.add_option = _compat_add_option


try:
    compat_Pattern = re.Pattern
except AttributeError:
    compat_Pattern = type(re.compile(''))


try:
    compat_Match = re.Match
except AttributeError:
    compat_Match = type(re.compile('').match(''))


try:
    compat_asyncio_run = asyncio.run  # >= 3.7
except AttributeError:
    def compat_asyncio_run(coro):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)

    asyncio.run = compat_asyncio_run


#  Deprecated

compat_basestring = str
compat_chr = chr
compat_input = input
compat_integer_types = (int, )
compat_kwargs = lambda kwargs: kwargs
compat_numeric_types = (int, float, complex)
compat_str = str
compat_xpath = lambda xpath: xpath
compat_zip = zip

compat_HTMLParser = html.parser.HTMLParser
compat_HTTPError = urllib.error.HTTPError
compat_Struct = struct.Struct
compat_b64decode = base64.b64decode
compat_cookiejar = http.cookiejar
compat_cookiejar_Cookie = compat_cookiejar.Cookie
compat_cookies = http.cookies
compat_cookies_SimpleCookie = compat_cookies.SimpleCookie
compat_etree_Element = etree.Element
compat_etree_register_namespace = etree.register_namespace
compat_expanduser = os.path.expanduser
compat_get_terminal_size = shutil.get_terminal_size
compat_getenv = os.getenv
compat_getpass = getpass.getpass
compat_html_entities = html.entities
compat_html_entities_html5 = compat_html_entities.html5
compat_http_client = http.client
compat_http_server = http.server
compat_itertools_count = itertools.count
compat_parse_qs = urllib.parse.parse_qs
compat_shlex_split = shlex.split
compat_socket_create_connection = socket.create_connection
compat_struct_pack = struct.pack
compat_struct_unpack = struct.unpack
compat_subprocess_get_DEVNULL = lambda: DEVNULL
compat_tokenize_tokenize = tokenize.tokenize
compat_urllib_error = urllib.error
compat_urllib_parse = urllib.parse
compat_urllib_parse_quote = urllib.parse.quote
compat_urllib_parse_quote_plus = urllib.parse.quote_plus
compat_urllib_parse_unquote = urllib.parse.unquote
compat_urllib_parse_unquote_plus = urllib.parse.unquote_plus
compat_urllib_parse_unquote_to_bytes = urllib.parse.unquote_to_bytes
compat_urllib_parse_urlencode = urllib.parse.urlencode
compat_urllib_parse_urlparse = urllib.parse.urlparse
compat_urllib_parse_urlunparse = urllib.parse.urlunparse
compat_urllib_request = urllib.request
compat_urllib_request_DataHandler = urllib.request.DataHandler
compat_urllib_response = urllib.response
compat_urlparse = urllib.parse
compat_urlretrieve = urllib.request.urlretrieve
compat_xml_parse_error = etree.ParseError


# Set public objects

__all__ = [
    'compat_HTMLParseError',
    'compat_HTMLParser',
    'compat_HTTPError',
    'compat_Match',
    'compat_Pattern',
    'compat_Struct',
    'compat_asyncio_run',
    'compat_b64decode',
    'compat_basestring',
    'compat_chr',
    'compat_cookiejar',
    'compat_cookiejar_Cookie',
    'compat_cookies',
    'compat_cookies_SimpleCookie',
    'compat_ctypes_WINFUNCTYPE',
    'compat_etree_Element',
    'compat_etree_fromstring',
    'compat_etree_register_namespace',
    'compat_expanduser',
    'compat_get_terminal_size',
    'compat_getenv',
    'compat_getpass',
    'compat_html_entities',
    'compat_html_entities_html5',
    'compat_http_client',
    'compat_http_server',
    'compat_input',
    'compat_integer_types',
    'compat_itertools_count',
    'compat_kwargs',
    'compat_numeric_types',
    'compat_ord',
    'compat_os_name',
    'compat_parse_qs',
    'compat_print',
    'compat_realpath',
    'compat_setenv',
    'compat_shlex_quote',
    'compat_shlex_split',
    'compat_socket_create_connection',
    'compat_str',
    'compat_struct_pack',
    'compat_struct_unpack',
    'compat_subprocess_get_DEVNULL',
    'compat_tokenize_tokenize',
    'compat_urllib_error',
    'compat_urllib_parse',
    'compat_urllib_parse_quote',
    'compat_urllib_parse_quote_plus',
    'compat_urllib_parse_unquote',
    'compat_urllib_parse_unquote_plus',
    'compat_urllib_parse_unquote_to_bytes',
    'compat_urllib_parse_urlencode',
    'compat_urllib_parse_urlparse',
    'compat_urllib_parse_urlunparse',
    'compat_urllib_request',
    'compat_urllib_request_DataHandler',
    'compat_urllib_response',
    'compat_urlparse',
    'compat_urlretrieve',
    'compat_xml_parse_error',
    'compat_xpath',
    'compat_zip',
    'workaround_optparse_bug9161',
]
