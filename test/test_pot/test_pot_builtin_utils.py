import pytest
from yt_dlp.extractor.youtube.pot.provider import (
    PoTokenContext,

)

from yt_dlp.extractor.youtube.pot.utils import get_webpo_content_binding, ContentBindingType


class TestGetWebPoContentBinding:

    @pytest.mark.parametrize('client_name, context, is_authenticated, expected', [
        *[(client, context, is_authenticated, expected) for client in [
            'WEB', 'MWEB', 'TVHTML5', 'WEB_EMBEDDED_PLAYER', 'WEB_CREATOR', 'TVHTML5_SIMPLY_EMBEDDED_PLAYER', 'TVHTML5_SIMPLY']
          for context, is_authenticated, expected in [
            (PoTokenContext.GVS, False, ('example-visitor-data', ContentBindingType.VISITOR_DATA)),
            (PoTokenContext.PLAYER, False, ('example-video-id', ContentBindingType.VIDEO_ID)),
            (PoTokenContext.SUBS, False, ('example-video-id', ContentBindingType.VIDEO_ID)),
            (PoTokenContext.GVS, True, ('example-data-sync-id', ContentBindingType.DATASYNC_ID)),
        ]],
        ('WEB_REMIX', PoTokenContext.GVS, False, ('example-visitor-data', ContentBindingType.VISITOR_DATA)),
        ('WEB_REMIX', PoTokenContext.PLAYER, False, ('example-visitor-data', ContentBindingType.VISITOR_DATA)),
        ('ANDROID', PoTokenContext.GVS, False, (None, None)),
        ('IOS', PoTokenContext.GVS, False, (None, None)),
    ])
    def test_get_webpo_content_binding(self, pot_request, client_name, context, is_authenticated, expected):
        pot_request.innertube_context['client']['clientName'] = client_name
        pot_request.context = context
        pot_request.is_authenticated = is_authenticated
        assert get_webpo_content_binding(pot_request) == expected

    def test_extract_visitor_id(self, pot_request):
        pot_request.visitor_data = 'CgsxMjNhYmNYWVpfLSiA4s%2DqBg%3D%3D'
        assert get_webpo_content_binding(pot_request, bind_to_visitor_id=True) == ('123abcXYZ_-', ContentBindingType.VISITOR_ID)

    def test_invalid_visitor_id(self, pot_request):
        # visitor id not alphanumeric (i.e. protobuf extraction failed)
        pot_request.visitor_data = 'CggxMjM0NTY3OCiA4s-qBg%3D%3D'
        assert get_webpo_content_binding(pot_request, bind_to_visitor_id=True) == (pot_request.visitor_data, ContentBindingType.VISITOR_DATA)

    def test_no_visitor_id(self, pot_request):
        pot_request.visitor_data = 'KIDiz6oG'
        assert get_webpo_content_binding(pot_request, bind_to_visitor_id=True) == (pot_request.visitor_data, ContentBindingType.VISITOR_DATA)

    def test_invalid_base64(self, pot_request):
        pot_request.visitor_data = 'invalid-base64'
        assert get_webpo_content_binding(pot_request, bind_to_visitor_id=True) == (pot_request.visitor_data, ContentBindingType.VISITOR_DATA)
