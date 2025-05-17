import pytest

from yt_dlp.extractor.youtube.pot._provider import IEContentProvider, BuiltinIEContentProvider
from yt_dlp.extractor.youtube.pot.cache import CacheProviderWritePolicy
from yt_dlp.utils import bug_reports_message
from yt_dlp.extractor.youtube.pot.provider import (
    PoTokenRequest,
    PoTokenContext,

)
from yt_dlp.version import __version__

from yt_dlp.extractor.youtube.pot._builtin.webpo_cachespec import WebPoPCSP
from yt_dlp.extractor.youtube.pot._registry import _pot_pcs_providers


@pytest.fixture()
def pot_request(pot_request) -> PoTokenRequest:
    pot_request.visitor_data = 'CgsxMjNhYmNYWVpfLSiA4s%2DqBg%3D%3D'  # visitor_id=123abcXYZ_-
    return pot_request


class TestWebPoPCSP:
    def test_base_type(self):
        assert issubclass(WebPoPCSP, IEContentProvider)
        assert issubclass(WebPoPCSP, BuiltinIEContentProvider)

    def test_init(self, ie, logger):
        pcs = WebPoPCSP(ie=ie, logger=logger, settings={})
        assert pcs.PROVIDER_NAME == 'webpo'
        assert pcs.PROVIDER_VERSION == __version__
        assert pcs.BUG_REPORT_MESSAGE == bug_reports_message(before='')
        assert pcs.is_available()

    def test_is_registered(self):
        assert _pot_pcs_providers.value.get('WebPo') == WebPoPCSP

    @pytest.mark.parametrize('client_name, context, is_authenticated', [
        ('ANDROID', PoTokenContext.GVS, False),
        ('IOS', PoTokenContext.GVS, False),
        ('IOS', PoTokenContext.PLAYER, False),
    ])
    def test_not_supports(self, ie, logger, pot_request, client_name, context, is_authenticated):
        pcs = WebPoPCSP(ie=ie, logger=logger, settings={})
        pot_request.innertube_context['client']['clientName'] = client_name
        pot_request.context = context
        pot_request.is_authenticated = is_authenticated
        assert pcs.generate_cache_spec(pot_request) is None

    @pytest.mark.parametrize('client_name, context, is_authenticated, remote_host, source_address, request_proxy, expected', [
        *[(client, context, is_authenticated, remote_host, source_address, request_proxy, expected) for client in [
            'WEB', 'MWEB', 'TVHTML5', 'WEB_EMBEDDED_PLAYER', 'WEB_CREATOR', 'TVHTML5_SIMPLY_EMBEDDED_PLAYER']
          for context, is_authenticated, remote_host, source_address, request_proxy, expected in [
            (PoTokenContext.GVS, False, 'example-remote-host', 'example-source-address', 'example-request-proxy', {'t': 'webpo', 'ip': 'example-remote-host', 'sa': 'example-source-address', 'px': 'example-request-proxy', 'cb': '123abcXYZ_-', 'cbt': 'visitor_id'}),
            (PoTokenContext.PLAYER, False, 'example-remote-host', 'example-source-address', 'example-request-proxy', {'t': 'webpo', 'ip': 'example-remote-host', 'sa': 'example-source-address', 'px': 'example-request-proxy', 'cb': '123abcXYZ_-', 'cbt': 'video_id'}),
            (PoTokenContext.GVS, True, 'example-remote-host', 'example-source-address', 'example-request-proxy', {'t': 'webpo', 'ip': 'example-remote-host', 'sa': 'example-source-address', 'px': 'example-request-proxy', 'cb': 'example-data-sync-id', 'cbt': 'datasync_id'}),
        ]],
        ('WEB_REMIX', PoTokenContext.PLAYER, False, 'example-remote-host', 'example-source-address', 'example-request-proxy', {'t': 'webpo', 'ip': 'example-remote-host', 'sa': 'example-source-address', 'px': 'example-request-proxy', 'cb': '123abcXYZ_-', 'cbt': 'visitor_id'}),
        ('WEB', PoTokenContext.GVS, False, None, None, None, {'t': 'webpo', 'cb': '123abcXYZ_-', 'cbt': 'visitor_id', 'ip': None, 'sa': None, 'px': None}),
        ('TVHTML5', PoTokenContext.PLAYER, False, None, None, 'http://example.com', {'t': 'webpo', 'cb': '123abcXYZ_-', 'cbt': 'video_id', 'ip': None, 'sa': None, 'px': 'http://example.com'}),

    ])
    def test_generate_key_bindings(self, ie, logger, pot_request, client_name, context, is_authenticated, remote_host, source_address, request_proxy, expected):
        pcs = WebPoPCSP(ie=ie, logger=logger, settings={})
        pot_request.innertube_context['client']['clientName'] = client_name
        pot_request.context = context
        pot_request.is_authenticated = is_authenticated
        pot_request.innertube_context['client']['remoteHost'] = remote_host
        pot_request.request_source_address = source_address
        pot_request.request_proxy = request_proxy
        pot_request.video_id = '123abcXYZ_-'  # same as visitor id to test type

        assert pcs.generate_cache_spec(pot_request).key_bindings == expected

    def test_no_bind_visitor_id(self, ie, logger, pot_request):
        # Should not bind to visitor id if setting is set to False
        pcs = WebPoPCSP(ie=ie, logger=logger, settings={'bind_to_visitor_id': ['false']})
        pot_request.innertube_context['client']['clientName'] = 'WEB'
        pot_request.context = PoTokenContext.GVS
        pot_request.is_authenticated = False
        assert pcs.generate_cache_spec(pot_request).key_bindings == {'t': 'webpo', 'ip': None, 'sa': None, 'px': None, 'cb': 'CgsxMjNhYmNYWVpfLSiA4s%2DqBg%3D%3D', 'cbt': 'visitor_data'}

    def test_default_ttl(self, ie, logger, pot_request):
        pcs = WebPoPCSP(ie=ie, logger=logger, settings={})
        assert pcs.generate_cache_spec(pot_request).default_ttl == 6 * 60 * 60  # should default to 6 hours

    def test_write_policy(self, ie, logger, pot_request):
        pcs = WebPoPCSP(ie=ie, logger=logger, settings={})
        pot_request.context = PoTokenContext.GVS
        assert pcs.generate_cache_spec(pot_request).write_policy == CacheProviderWritePolicy.WRITE_ALL
        pot_request.context = PoTokenContext.PLAYER
        assert pcs.generate_cache_spec(pot_request).write_policy == CacheProviderWritePolicy.WRITE_FIRST
