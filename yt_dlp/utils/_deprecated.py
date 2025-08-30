"""Deprecated - New code should avoid these"""
import base64
import hashlib
import hmac
import json
import warnings

from ..compat.compat_utils import passthrough_module

# XXX: Implement this the same way as other DeprecationWarnings without circular import
passthrough_module(__name__, '.._legacy', callback=lambda attr: warnings.warn(
    DeprecationWarning(f'{__name__}.{attr} is deprecated'), stacklevel=6))
del passthrough_module


import re
import struct


def bytes_to_intlist(bs):
    if not bs:
        return []
    if isinstance(bs[0], int):  # Python 3
        return list(bs)
    else:
        return [ord(c) for c in bs]


def intlist_to_bytes(xs):
    if not xs:
        return b''
    return struct.pack('%dB' % len(xs), *xs)


def jwt_encode_hs256(payload_data, key, headers={}):
    header_data = {
        'alg': 'HS256',
        'typ': 'JWT',
    }
    if headers:
        header_data.update(headers)
    header_b64 = base64.b64encode(json.dumps(header_data).encode())
    payload_b64 = base64.b64encode(json.dumps(payload_data).encode())
    h = hmac.new(key.encode(), header_b64 + b'.' + payload_b64, hashlib.sha256)
    signature_b64 = base64.b64encode(h.digest())
    return header_b64 + b'.' + payload_b64 + b'.' + signature_b64


compiled_regex_type = type(re.compile(''))
