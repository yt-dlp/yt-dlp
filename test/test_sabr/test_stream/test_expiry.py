from __future__ import annotations
import re
import time
from unittest.mock import MagicMock
import pytest

from test.test_sabr.test_stream.helpers import setup_sabr_stream_av, Respond403Processor, mock_time, collect_parts
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import SabrUrlExpired, SabrStreamError
from yt_dlp.extractor.youtube._streaming.sabr.models import ReloadConfigReason
from yt_dlp.extractor.youtube._streaming.sabr.stream import ReloadConfigRequest


def test_expiry_threshold_sec_validation(logger, client_info):
    # Should raise ValueError if expiry_threshold_sec is negative
    with pytest.raises(ValueError, match='expiry_threshold_sec must be greater than 0'):
        setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            expiry_threshold_sec=-10,
        )


def test_expiry_reload_config(logger, client_info, reload_callback_response):
    # Should call the reload config callback if within the expiry time
    expires_at = int(time.time() + 30)  # 30 seconds from now

    reload_config_callback = MagicMock()
    reload_config_callback.side_effect = lambda _: reload_callback_response

    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        reload_callback=reload_config_callback,
        # By default, expiry threshold is 60 seconds
    )
    stats_str = sabr_stream.create_stats_str()
    assert re.search(r'exp:0:00:\d{1,2}', stats_str)

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token

    # Retrieve parts until the callback is called
    while not reload_config_callback.called:
        next(sabr_stream.iter_parts())

    reload_config_callback.assert_called_with(ReloadConfigRequest(reason=ReloadConfigReason.SABR_URL_EXPIRY))
    logger.debug.assert_any_call(
        r'Requesting config refresh as the URL is due to expire within 60 seconds')

    # Should have applied the reloaded config
    stats_str = sabr_stream.create_stats_str()
    assert re.search(r'exp:0:09:\d{2}', stats_str)

    assert sabr_stream.url == reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config == reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info == reload_callback_response.client_info
    assert sabr_stream.processor.po_token == reload_callback_response.po_token


def test_expiry_threshold_sec(logger, client_info, reload_callback_response):
    # Should use the configured expiry threshold seconds when determining to reload config
    reload_config_callback = MagicMock()
    reload_config_callback.side_effect = lambda _: reload_callback_response

    expires_at = int(time.time() + 100)  # 100 seconds from now
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        expiry_threshold_sec=120,  # Set threshold to 2 minutes
        reload_callback=reload_config_callback,
    )

    # Retrieve parts until the callback is called
    while not reload_config_callback.called:
        next(sabr_stream.iter_parts())

    reload_config_callback.assert_called_with(ReloadConfigRequest(reason=ReloadConfigReason.SABR_URL_EXPIRY))
    logger.debug.assert_any_call(
        r'Requesting config refresh as the URL is due to expire within 120 seconds')


def test_no_expiry_in_url(logger, client_info, reload_callback_response):
    # Should not reload config if no expiry in URL
    # It should log a warning about missing expiry
    reload_config_callback = MagicMock()
    reload_config_callback.side_effect = lambda _: reload_callback_response
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url='https://noexpire.googlevideo.com?sabr=1',
        reload_callback=reload_config_callback,
    )
    collect_parts(sabr_stream)
    logger.warning.assert_called_with(
        'No expiry timestamp found in URL. Will not be able to refresh.', once=True)
    reload_config_callback.assert_not_called()


@mock_time
def test_not_expired(logger, client_info, reload_callback_response):
    # Should not reload config if not within the expiry threshold
    reload_config_callback = MagicMock()
    reload_config_callback.side_effect = lambda _: reload_callback_response
    expires_at = int(time.time() + 300)  # 5 minutes from now
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?expire={int(expires_at)}&sabr=1',
        # By default, expiry threshold is 60 seconds
    )
    collect_parts(sabr_stream)
    reload_config_callback.assert_not_called()
    logger.trace.assert_any_call('URL expires in 300 seconds')


def test_expired_403(logger, client_info):
    # If the URL has expired and the server gives a 403, should throw a SabrUrlExpired error
    # No callback is registered in this test
    expires_at = int(time.time() - 1)  # already expired
    sabr_stream, rh, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?expire={int(expires_at)}&sabr=1',
        sabr_response_processor=Respond403Processor(),
    )

    with pytest.raises(
        SabrUrlExpired,
        match=r'SABR URL has expired. The download will need to be restarted.',
    ):
        collect_parts(sabr_stream)

    assert len(rh.request_history) == 1
    assert rh.request_history[0].response.status == 403

    # All responses should be closed
    assert all(request.response.closed for request in rh.request_history)

    logger.debug.assert_any_call('No reload callback provided, skipping config reload')


def test_non_expired_403(logger, client_info):
    # Sanity check: if we get a 403 but url has not expired, should give a SabrStreamError
    expires_at = int(time.time() + 300)  # not expired

    sabr_stream, rh, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?expire={int(expires_at)}&sabr=1',
        sabr_response_processor=Respond403Processor(),
    )
    with pytest.raises(
        SabrStreamError,
        match='HTTP Error: 403 - Forbidden',
    ):
        collect_parts(sabr_stream)

    assert len(rh.request_history) == 1
    assert rh.request_history[0].response.status == 403

    # All responses should be closed
    assert all(request.response.closed for request in rh.request_history)


def test_no_expiry_403(logger, client_info):
    # Sanity check: if we get a 403 but url has no expiry, should give a SabrStreamError
    sabr_stream, rh, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url='https://expire.googlevideo.com/sabr?sabr=1',
        sabr_response_processor=Respond403Processor(),
    )
    with pytest.raises(
        SabrStreamError,
        match='HTTP Error: 403 - Forbidden',
    ):
        collect_parts(sabr_stream)

    assert len(rh.request_history) == 1
    assert rh.request_history[0].response.status == 403

    # All responses should be closed
    assert all(request.response.closed for request in rh.request_history)
