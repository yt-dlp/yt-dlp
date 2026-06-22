from __future__ import annotations

from yt_dlp.extractor.youtube.jsc._builtin.deno import DenoJCP
from yt_dlp.utils._jsruntime import JsRuntimeInfo


class FakeRuntime:
    MIN_SUPPORTED_VERSION = (2, 3, 0)

    def __init__(self, supported):
        self.info = JsRuntimeInfo(
            name='deno',
            path='deno',
            version='2.2.0',
            version_tuple=(2, 2, 0),
            supported=supported)


def test_unsupported_js_runtime_warning(ie, logger):
    warnings = []
    ie.report_warning = lambda message, **kwargs: warnings.append((message, kwargs))
    ie._downloader._js_runtimes['deno'] = FakeRuntime(supported=False)

    provider = DenoJCP(ie=ie, logger=logger, settings={})

    assert provider.is_available() is False
    assert warnings == [(
        'deno version 2.2.0 is not supported and cannot be used for YouTube JS challenges. '
        'deno >= 2.3.0 is required. Please update deno or enable another JS runtime with --js-runtimes.',
        {'only_once': True},
    )]


def test_supported_js_runtime_available(ie, logger):
    warnings = []
    ie.report_warning = lambda message, **kwargs: warnings.append((message, kwargs))
    ie._downloader._js_runtimes['deno'] = FakeRuntime(supported=True)

    provider = DenoJCP(ie=ie, logger=logger, settings={})

    assert provider.is_available() is True
    assert warnings == []
