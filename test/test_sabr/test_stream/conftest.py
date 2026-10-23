import base64
import dataclasses
import time
import pytest
from yt_dlp.extractor.youtube._streaming.sabr.stream import ReloadConfigResponse


@pytest.fixture
def reload_callback_response(client_info):
    new_client_info = dataclasses.replace(client_info, client_version='2.0')
    return ReloadConfigResponse(
        client_info=new_client_info,
        video_playback_ustreamer_config=base64.urlsafe_b64encode(b'new-config').decode('utf-8'),
        server_abr_streaming_url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(time.time() + 600)}',
        po_token=base64.urlsafe_b64encode(b'new-token').decode('utf-8'))
