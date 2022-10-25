""" Do not use! """

import collections
import ctypes
import getpass
import html.entities
import html.parser
import http.client
import http.cookiejar
import http.cookies
import http.server
import itertools
import os
import shlex
import shutil
import socket
import struct
import tokenize
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as etree
from subprocess import DEVNULL

# isort: split
import asyncio  # noqa: F401
import re  # noqa: F401
from asyncio import run as compat_asyncio_run  # noqa: F401
from re import Pattern as compat_Pattern  # noqa: F401
from re import match as compat_Match  # noqa: F401

from .compat_utils import passthrough_module
from ..dependencies import Cryptodome_AES as compat_pycrypto_AES  # noqa: F401
from ..dependencies import brotli as compat_brotli  # noqa: F401
from ..dependencies import websockets as compat_websockets  # noqa: F401

passthrough_module(__name__, '...utils', ('WINDOWS_VT_MODE', 'windows_enable_vt_mode'))


# compat_ctypes_WINFUNCTYPE = ctypes.WINFUNCTYPE
# will not work since ctypes.WINFUNCTYPE does not exist in UNIX machines
def compat_ctypes_WINFUNCTYPE(*args, **kwargs):
    return ctypes.WINFUNCTYPE(*args, **kwargs)


def compat_setenv(key, value, env=os.environ):
    env[key] = value


compat_basestring = str
compat_chr = chr
compat_collections_abc = collections.abc
compat_cookiejar = http.cookiejar
compat_cookiejar_Cookie = http.cookiejar.Cookie
compat_cookies = http.cookies
compat_cookies_SimpleCookie = http.cookies.SimpleCookie
compat_etree_Element = etree.Element
compat_etree_register_namespace = etree.register_namespace
compat_filter = filter
compat_get_terminal_size = shutil.get_terminal_size
compat_getenv = os.getenv
compat_getpass = getpass.getpass
compat_html_entities = html.entities
compat_html_entities_html5 = html.entities.html5
compat_HTMLParser = html.parser.HTMLParser
compat_http_client = http.client
compat_http_server = http.server
compat_input = input
compat_integer_types = (int, )
compat_itertools_count = itertools.count
compat_kwargs = lambda kwargs: kwargs
compat_map = map
compat_numeric_types = (int, float, complex)
compat_print = print
compat_shlex_split = shlex.split
compat_socket_create_connection = socket.create_connection
compat_Struct = struct.Struct
compat_struct_pack = struct.pack
compat_struct_unpack = struct.unpack
compat_subprocess_get_DEVNULL = lambda: DEVNULL
compat_tokenize_tokenize = tokenize.tokenize
compat_urllib_error = urllib.error
compat_urllib_parse = urllib.parse
compat_urllib_parse_quote = urllib.parse.quote
compat_urllib_parse_quote_plus = urllib.parse.quote_plus
compat_urllib_parse_unquote_plus = urllib.parse.unquote_plus
compat_urllib_parse_unquote_to_bytes = urllib.parse.unquote_to_bytes
compat_urllib_parse_urlunparse = urllib.parse.urlunparse
compat_urllib_request = urllib.request
compat_urllib_request_DataHandler = urllib.request.DataHandler
compat_urllib_response = urllib.response
compat_urlretrieve = urllib.request.urlretrieve
compat_xml_parse_error = etree.ParseError
compat_xpath = lambda xpath: xpath
compat_zip = zip
workaround_optparse_bug9161 = lambda: None
