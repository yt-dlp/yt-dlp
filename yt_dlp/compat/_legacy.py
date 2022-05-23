""" Do not use! """

import collections
import ctypes
import http
import http.client
import http.cookiejar
import http.cookies
import http.server
import shlex
import socket
import struct
import urllib
import xml.etree.ElementTree as etree
from subprocess import DEVNULL

from .asyncio import run as compat_asyncio_run  # noqa: F401
from .re import Pattern as compat_Pattern  # noqa: F401
from .re import match as compat_Match  # noqa: F401
from ..dependencies import Cryptodome_AES as compat_pycrypto_AES  # noqa: F401
from ..dependencies import brotli as compat_brotli  # noqa: F401
from ..dependencies import websockets as compat_websockets  # noqa: F401


# compat_ctypes_WINFUNCTYPE = ctypes.WINFUNCTYPE
# will not work since ctypes.WINFUNCTYPE does not exist in UNIX machines
def compat_ctypes_WINFUNCTYPE(*args, **kwargs):
    return ctypes.WINFUNCTYPE(*args, **kwargs)


compat_basestring = str
compat_collections_abc = collections.abc
compat_cookies = http.cookies
compat_etree_Element = etree.Element
compat_etree_register_namespace = etree.register_namespace
compat_filter = filter
compat_input = input
compat_integer_types = (int, )
compat_kwargs = lambda kwargs: kwargs
compat_map = map
compat_numeric_types = (int, float, complex)
compat_print = print
compat_shlex_split = shlex.split
compat_socket_create_connection = socket.create_connection
compat_Struct = struct.Struct
compat_subprocess_get_DEVNULL = lambda: DEVNULL
compat_urllib_parse_quote = urllib.parse.quote
compat_urllib_parse_quote_plus = urllib.parse.quote_plus
compat_urllib_parse_unquote_to_bytes = urllib.parse.unquote_to_bytes
compat_urllib_parse_urlunparse = urllib.parse.urlunparse
compat_urllib_request_DataHandler = urllib.request.DataHandler
compat_urllib_response = urllib.response
compat_urlretrieve = urllib.request.urlretrieve
compat_xml_parse_error = etree.ParseError
compat_xpath = lambda xpath: xpath
compat_zip = zip
workaround_optparse_bug9161 = lambda: None


def __getattr__(name):
    if name in ('WINDOWS_VT_MODE', 'windows_enable_vt_mode'):
        from .. import utils
        return getattr(utils, name)
    raise AttributeError(name)
