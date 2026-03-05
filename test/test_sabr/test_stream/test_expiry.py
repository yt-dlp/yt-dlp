from __future__ import annotations
import re
import time
import pytest

from test.test_sabr.test_stream.helpers import setup_sabr_stream_av
from yt_dlp.extractor.youtube._streaming.sabr.part import RefreshPlayerResponseSabrPart


def test_expiry_threshold_sec_validation(logger, client_info):
    # Should raise ValueError if expiry_threshold_sec is negative
    with pytest.raises(ValueError, match='expiry_threshold_sec must be greater than 0'):
        setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            expiry_threshold_sec=-10,
        )


def test_expiry_refresh_player_response(logger, client_info):
    # Should yield a refresh player response part if within the expiry time
    # This should occur before the next request
    expires_at = int(time.time() + 30)  # 30 seconds from now
    sabr_stream, rh, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        # By default, expiry threshold is 60 seconds
    )
    # Retrieve parts until we get a RefreshPlayerResponseSabrPart
    refresh_part = None
    while not refresh_part:
        part = next(sabr_stream.iter_parts())
        if isinstance(part, RefreshPlayerResponseSabrPart):
            refresh_part = part
    # Should be no requests made so far as checking expiry happens before request
    assert len(rh.request_history) == 0
    assert refresh_part is not None
    assert refresh_part.reason == RefreshPlayerResponseSabrPart.Reason.SABR_URL_EXPIRY
    logger.debug.assert_called_with(
        r'Requesting player response refresh as SABR URL is due to expire within 60 seconds')

    stats_str = sabr_stream.create_stats_str()
    assert re.search(r'exp:0:00:\d{1,2}', stats_str)


def test_expiry_threshold_sec(logger, client_info):
    # Should use the configured expiry threshold seconds when determining to refresh player response
    expires_at = int(time.time() + 100)  # 100 seconds from now
    sabr_stream, rh, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        expiry_threshold_sec=120,  # Set threshold to 2 minutes
    )

    # Retrieve parts until we get a RefreshPlayerResponseSabrPart
    refresh_part = None
    while not refresh_part:
        part = next(sabr_stream.iter_parts())
        if isinstance(part, RefreshPlayerResponseSabrPart):
            refresh_part = part
    # Should be no requests made so far as checking expiry happens before request
    assert len(rh.request_history) == 0
    assert refresh_part is not None
    assert refresh_part.reason == RefreshPlayerResponseSabrPart.Reason.SABR_URL_EXPIRY
    logger.debug.assert_called_with(
        r'Requesting player response refresh as SABR URL is due to expire within 120 seconds')


def test_no_expiry_in_url(logger, client_info):
    # Should not yield a refresh player response part if no expiry in URL
    # It should log a warning about missing expiry
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url='https://noexpire.googlevideo.com?sabr=1',
    )
    parts = list(sabr_stream.iter_parts())
    assert all(not isinstance(part, RefreshPlayerResponseSabrPart) for part in parts)
    logger.warning.assert_called_with('No expiry timestamp found in SABR URL. Will not be able to refresh.',
                                      once=True)


def test_not_expired(logger, client_info):
    # Should not yield a refresh player response part if not within the expiry threshold
    expires_at = int(time.time() + 300)  # 5 minutes from now
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?expire={int(expires_at)}&sabr=1',
        # By default, expiry threshold is 60 seconds
    )
    parts = list(sabr_stream.iter_parts())
    assert all(not isinstance(part, RefreshPlayerResponseSabrPart) for part in parts)
