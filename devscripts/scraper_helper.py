# coding: utf-8
from __future__ import unicode_literals

import re

from yt_dlp.utils import ExtractorError, traverse_obj
from yt_dlp.extractor.common import InfoExtractor
from test.helper import FakeYDL


class TestIE(InfoExtractor):
    pass


ie = TestIE(FakeYDL({
    'verbose': False,
    'socket_timeout': 120,
}))

orig_dwh = ie._download_webpage_handle

dwh_args = orig_dwh.__code__.co_varnames[1:orig_dwh.__code__.co_argcount]


def retry_download_webpage_handle(*args, **kw):
    kw = {
        **dict(zip(dwh_args, args)),
        **kw,
    }
    retries = 3
    fatal = kw.get('fatal', True)
    note = kw.get('note')
    kw['fatal'] = True
    for i in range(retries + 1):
        try:
            if i:
                kw['note'] = f'{note} (retry {i} of {retries})'
            return orig_dwh(**kw)
        except ExtractorError as e:
            if retries == i + 1:
                if fatal:
                    raise
                else:
                    ie.report_warning(e)
                    break
            ie.report_warning(f'{e} Retrying...')


ie._download_webpage_handle = retry_download_webpage_handle


def sanitize_hostname(hostname):
    # trim trailing slashes
    hostname = re.sub(r'[/\\]+$', '', hostname)
    # trim port number
    hostname = re.sub(r':\d+$', '', hostname)
    return hostname


def traverse_sanitize(*arg, **kw):
    return map(sanitize_hostname, traverse_obj(*arg, **kw) or [])
