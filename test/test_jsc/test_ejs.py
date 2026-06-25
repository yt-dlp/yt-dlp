from __future__ import annotations

from yt_dlp.extractor.youtube.jsc._builtin.deno import DenoJCP
from yt_dlp.utils._jsruntime import JsRuntimeInfo


class FakeRuntime:
    def __init__(self, supported):
        self.info = JsRuntimeInfo(
            name='deno',
            path='deno',
            version='2.2.0',
            version_tuple=(2, 2, 0),
            supported=supported,
            unsupported_reason=None if supported else 'deno >= 2.3.0 is required')


def test_unsupported_js_runtime_warning(ie, logger):
    warnings = []
    ie.report_warning = lambda message, **kwargs: warnings.append(message)
    ie._downloader._js_runtimes['deno'] = FakeRuntime(supported=False)

    provider = DenoJCP(ie=ie, logger=logger, settings={})

    assert provider.is_available() is False
    assert len(warnings) == 1
    assert 'not supported' in warnings[0]


def test_supported_js_runtime_available(ie, logger):
    warnings = []
    ie.report_warning = lambda message, **kwargs: warnings.append(message)
    ie._downloader._js_runtimes['deno'] = FakeRuntime(supported=True)

    provider = DenoJCP(ie=ie, logger=logger, settings={})

    assert provider.is_available() is True
    assert warnings == []
