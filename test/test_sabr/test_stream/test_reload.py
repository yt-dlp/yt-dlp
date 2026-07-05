from __future__ import annotations
import base64
import time
from unittest.mock import MagicMock
import pytest

from test.test_sabr.test_stream.helpers import (
    setup_sabr_stream_av,
    DEFAULT_NUM_AUDIO_SEGMENTS,
    assert_media_sequence_in_order,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    VIDEO_ID,
    mock_time,
    collect_parts,
)
from yt_dlp.extractor.youtube._proto.videostreaming import SabrContextUpdate, AdCuepointConfig
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import BroadcastIdChanged

# Specific tests for testing the reload config callback behavior.

EXPIRES_SOON_URL = f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(time.time() + 30)}'


def test_exception(logger, client_info):
    # Should warn and continue on an exception from the reload config callback
    reload_config_callback = MagicMock()
    reload_config_callback.side_effect = Exception('callback error')

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.warning.assert_any_call(
        "Error occurred while calling reload callback: Exception('callback error')")


def test_no_response(logger, client_info):
    # Should write to debug and continue on no response from the reload config callback
    reload_config_callback = MagicMock()
    reload_config_callback.return_value = None

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.debug.assert_any_call('Reload callback returned no response')


def test_invalid_response_object(logger, client_info):
    # Should warn and continue if the reload config callback returns an invalid object
    reload_config_callback = MagicMock()
    reload_config_callback.return_value = 'invalid'

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.warning.assert_any_call(
        "Invalid reload response: not a ReloadConfigResponse: 'invalid'")


@pytest.mark.parametrize('item,value', [
    ('video_playback_ustreamer_config', None),
    ('video_playback_ustreamer_config', 123),
    ('server_abr_streaming_url', None),
    ('server_abr_streaming_url', 123),
])
def test_invalid_response_value(logger, client_info, reload_callback_response, item, value):
    # Should warn and continue if the reload config callback returns a response with missing or invalid values
    reload_config_callback = MagicMock()
    setattr(reload_callback_response, item, value)
    reload_config_callback.return_value = reload_callback_response

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.warning.assert_any_call(
        f'Invalid reload response: missing or invalid {item}: {value!r}')

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token


def test_missing_client_info(logger, client_info, reload_callback_response):
    # Should warn and continue if the reload config callback is missing client_info
    reload_config_callback = MagicMock()
    reload_callback_response.client_info = None
    reload_config_callback.return_value = reload_callback_response

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.warning.assert_any_call(
        'Invalid reload response: missing or invalid client_info: None')

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token


def test_invalid_client_info(logger, client_info, reload_callback_response):
    # Should warn and continue if the reload config callback returns an invalid client_info object
    reload_config_callback = MagicMock()
    reload_callback_response.client_info = 'not-client-info'
    reload_config_callback.return_value = reload_callback_response

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.warning.assert_any_call(
        "Invalid reload response: missing or invalid client_info: 'not-client-info'")

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token


def test_client_info_client_name_mismatch(logger, client_info, reload_callback_response):
    # Should warn and continue if the reload config callback returns a client_info with a different client_name than the original
    reload_config_callback = MagicMock()
    reload_callback_response.client_info.client_name = 'MWEB'
    reload_config_callback.return_value = reload_callback_response

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.warning.assert_any_call('Client name in reload response does not match current client name: MWEB != WEB')

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token


def test_video_id_mismatch(logger, client_info, reload_callback_response):
    # Should warn and continue if the reload config callback video_id mismatches the one associated with the stream
    reload_config_callback = MagicMock()
    reload_callback_response.video_id = 'mismatch'
    reload_config_callback.return_value = reload_callback_response

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
        video_id=VIDEO_ID,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.warning.assert_any_call(f'Video ID in reload response does not match current video ID: mismatch != {VIDEO_ID}')

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token


def test_invalid_pot(logger, client_info, reload_callback_response):
    # Should warn and continue if the reload config callback returns an invalid pot
    reload_config_callback = MagicMock()
    reload_callback_response.po_token = 123
    reload_config_callback.return_value = reload_callback_response

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.warning.assert_any_call('Invalid reload response: po_token is not a string: 123')

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token


def test_no_po_token(logger, client_info, reload_callback_response):
    # Should reload the config if there is no po_token. Should not replace existing po_token.
    expires_at = int(time.time() + 30)  # 30 seconds from now

    reload_callback_response.po_token = None
    reload_config_callback = MagicMock()
    reload_config_callback.return_value = reload_callback_response
    po_token = base64.b64encode(b'valid-po-token')
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        reload_callback=reload_config_callback,
        po_token=po_token,
    )

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token

    # Retrieve parts until the callback is called
    while not reload_config_callback.called:
        next(sabr_stream.iter_parts())

    reload_config_callback.assert_called()

    # Should have applied the reloaded config
    assert sabr_stream.url == reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config == reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info == reload_callback_response.client_info
    assert sabr_stream.processor.po_token == po_token


def test_video_id_matches(logger, client_info, reload_callback_response):
    # Should reload the config if video_id matches.
    expires_at = int(time.time() + 30)  # 30 seconds from now

    reload_callback_response.video_id = VIDEO_ID
    reload_config_callback = MagicMock()
    reload_config_callback.return_value = reload_callback_response
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        reload_callback=reload_config_callback,
        video_id=VIDEO_ID,
    )

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token

    # Retrieve parts until the callback is called
    while not reload_config_callback.called:
        next(sabr_stream.iter_parts())

    reload_config_callback.assert_called()

    # Should have applied the reloaded config
    assert sabr_stream.url == reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config == reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info == reload_callback_response.client_info
    assert sabr_stream.processor.po_token == reload_callback_response.po_token


def test_video_id_unavailable(logger, client_info, reload_callback_response):
    # Should reload the config if video_id provided in response but no video_id is associated with the stream.
    expires_at = int(time.time() + 30)  # 30 seconds from now

    reload_callback_response.video_id = VIDEO_ID
    reload_config_callback = MagicMock()
    reload_config_callback.return_value = reload_callback_response
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        reload_callback=reload_config_callback,
    )

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token

    # Retrieve parts until the callback is called
    while not reload_config_callback.called:
        next(sabr_stream.iter_parts())

    reload_config_callback.assert_called()

    # Should have applied the reloaded config
    assert sabr_stream.url == reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config == reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info == reload_callback_response.client_info
    assert sabr_stream.processor.po_token == reload_callback_response.po_token


@pytest.mark.parametrize('post_live', [True, False], ids=['post_live=True', 'post_live=False'])
@mock_time
def test_live_error_on_broadcast_id_update(logger, client_info, post_live, reload_callback_response):
    # Should raise an error if broadcast_id changes for live stream on reload. Post live flag should not affect this.

    expires_at = int(time.time() + 30)  # 30 seconds from now
    reload_callback_response.server_abr_streaming_url = 'https://live.googlevideo.com/sabr?sabr=1&source=yt_live_broadcast&id=xyz.2'
    reload_config_callback = MagicMock()
    reload_config_callback.return_value = reload_callback_response

    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://live.googlevideo.com/sabr?sabr=1&source=yt_live_broadcast&id=xyz.1&expire={expires_at}',
        post_live=post_live,
        reload_callback=reload_config_callback,
    )

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token

    assert sabr_stream.processor.is_live is True
    with pytest.raises(BroadcastIdChanged, match=r'Broadcast ID changed from 1 to 2\.'):
        collect_parts(sabr_stream)

    reload_config_callback.assert_called()

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token


def test_clear_ad_contexts(logger, client_info, reload_callback_response):
    # Should clear the ad contexts in the processor on reload
    expires_at = int(time.time() + 30)  # 30 seconds from now

    reload_callback_response.video_id = VIDEO_ID
    reload_config_callback = MagicMock()
    reload_config_callback.return_value = reload_callback_response
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        reload_callback=reload_config_callback,
    )

    sabr_stream.processor.sabr_contexts_to_send = [2]
    sabr_stream.processor.sabr_context_updates[2] = SabrContextUpdate(
        type=2,
        scope=SabrContextUpdate.SabrContextScope.REQUEST,
        value=b'xyz',
        write_policy=SabrContextUpdate.SabrContextWritePolicy.OVERWRITE,
        send_by_default=True,
    )
    sabr_stream.processor.ad_cuepoints['xyz'] = AdCuepointConfig(cuepoint_id='xyz')

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token

    # Retrieve parts until the callback is called
    while not reload_config_callback.called:
        next(sabr_stream.iter_parts())

    reload_config_callback.assert_called()

    # Should have applied the reloaded config
    assert sabr_stream.url == reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config == reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info == reload_callback_response.client_info
    assert sabr_stream.processor.po_token == reload_callback_response.po_token

    # Should have cleared ad context information in processor
    assert len(sabr_stream.processor.ad_cuepoints) == 0
    assert len(sabr_stream.processor.sabr_contexts_to_send) == 0
    assert len(sabr_stream.processor.sabr_context_updates) == 0


def test_new_callbacks(logger, client_info, reload_callback_response):
    # Should reload the config with new callbacks
    expires_at = int(time.time() + 30)  # 30 seconds from now

    reload_callback_response.pot_callback = lambda _: None
    reload_callback_response.heartbeat_callback = lambda _: None
    reload_callback_response.reload_callback = lambda _: None

    reload_config_callback = MagicMock()
    reload_config_callback.return_value = reload_callback_response
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        reload_callback=reload_config_callback,
    )

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token

    # Retrieve parts until the callback is called
    while not reload_config_callback.called:
        next(sabr_stream.iter_parts())

    reload_config_callback.assert_called()

    # Should have applied the reloaded config
    assert sabr_stream.url == reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config == reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info == reload_callback_response.client_info
    assert sabr_stream.processor.po_token == reload_callback_response.po_token
    assert sabr_stream._reload_callback is not reload_config_callback
    assert sabr_stream._reload_callback is reload_callback_response.reload_callback
    assert sabr_stream._pot_callback is reload_callback_response.pot_callback
    assert sabr_stream._heartbeat_callback is reload_callback_response.heartbeat_callback


def test_not_replace_callbacks(logger, client_info, reload_callback_response):
    # Should not replace existing callbacks if the response does not contain them
    expires_at = int(time.time() + 30)  # 30 seconds from now

    reload_config_callback = MagicMock()
    reload_config_callback.return_value = reload_callback_response
    sabr_stream, _, _ = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=f'https://expire.googlevideo.com/sabr?sabr=1&expire={int(expires_at)}',
        reload_callback=reload_config_callback,
        heartbeat_callback=MagicMock(),
        pot_callback=MagicMock(),
    )

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token

    # Retrieve parts until the callback is called
    while not reload_config_callback.called:
        next(sabr_stream.iter_parts())

    reload_config_callback.assert_called()

    # Should have applied the reloaded config
    assert sabr_stream.url == reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config == reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info == reload_callback_response.client_info
    assert sabr_stream.processor.po_token == reload_callback_response.po_token

    # Should not overwrite existing callbacks
    assert sabr_stream._reload_callback is reload_config_callback
    assert sabr_stream._pot_callback is not None
    assert sabr_stream._heartbeat_callback is not None


@pytest.mark.parametrize('item,value', [
    ('heartbeat_callback', 123),
    ('pot_callback', 123),
    ('reload_callback', 123),
])
def test_invalid_callback_value(logger, client_info, reload_callback_response, item, value):
    # Should warn and continue if one of the callback values is invalid
    reload_config_callback = MagicMock()
    setattr(reload_callback_response, item, value)
    reload_config_callback.return_value = reload_callback_response

    sabr_stream, _, selectors = setup_sabr_stream_av(
        client_info=client_info,
        logger=logger,
        url=EXPIRES_SOON_URL,
        reload_callback=reload_config_callback,
    )
    audio_selector, video_selector = selectors

    parts = collect_parts(sabr_stream)

    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    reload_config_callback.assert_called()
    logger.warning.assert_any_call(
        f'Invalid reload response: invalid callback function for {item}: {value!r}')

    assert sabr_stream.url != reload_callback_response.server_abr_streaming_url
    assert sabr_stream.processor.video_playback_ustreamer_config != reload_callback_response.video_playback_ustreamer_config
    assert sabr_stream.processor.client_info != reload_callback_response.client_info
    assert sabr_stream.processor.po_token != reload_callback_response.po_token
    assert sabr_stream._reload_callback is reload_config_callback
    assert sabr_stream._pot_callback is None
    assert sabr_stream._heartbeat_callback is None
