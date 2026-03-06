from __future__ import annotations

from test.test_sabr.test_stream.helpers import (
    DEFAULT_NUM_AUDIO_SEGMENTS,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    assert_media_sequence_in_order,
    AdWaitAVProfile,
    SabrContextSendingPolicyAVProfile,
    mock_time,
    setup_sabr_stream_av,
)

from yt_dlp.extractor.youtube._proto.videostreaming import SabrContext


@mock_time
def test_ad_wait(logger, client_info):
    # Should send back SabrContextUpdate and wait the specified time in the next request policy
    sabr_stream, rh, selectors = setup_sabr_stream_av(
        sabr_response_processor=AdWaitAVProfile(),
        client_info=client_info,
        logger=logger,
    )
    audio_selector, video_selector = selectors

    parts = list(sabr_stream.iter_parts())
    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    # Second request should be sending the ad wait sabr context update
    ad_wait_request_vpabr = rh.request_history[1].vpabr
    assert len(ad_wait_request_vpabr.streamer_context.sabr_contexts) == 1
    assert ad_wait_request_vpabr.streamer_context.sabr_contexts[0] == SabrContext(
        type=AdWaitAVProfile.CONTEXT_UPDATE_TYPE,
        value=AdWaitAVProfile.CONTEXT_UPDATE_DATA,
    )

    # SabrStream rounds up the wait time to nearest second
    logger.info.assert_any_call('Sleeping 1.00 seconds as required by the server')

    assert AdWaitAVProfile.CONTEXT_UPDATE_TYPE in sabr_stream.processor.sabr_context_updates
    assert sabr_stream.processor.sabr_context_updates[5].value == AdWaitAVProfile.CONTEXT_UPDATE_DATA
    assert sabr_stream.processor.sabr_context_updates[5].scope >= AdWaitAVProfile.CONTEXT_UPDATE_SCOPE
    assert AdWaitAVProfile.CONTEXT_UPDATE_TYPE in sabr_stream.processor.sabr_contexts_to_send

    stats_str = sabr_stream.create_stats_str()
    assert 'cu:[5]' in stats_str


def test_sending_policy(logger, client_info):
    # Should respect the sending policy part to update sabr context state
    sabr_stream, rh, selectors = setup_sabr_stream_av(
        sabr_response_processor=SabrContextSendingPolicyAVProfile(),
        client_info=client_info,
        logger=logger,
    )
    audio_selector, video_selector = selectors
    parts = list(sabr_stream.iter_parts())
    assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
    assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

    context_update_type = SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_TYPE

    # Request should include the sabr context update
    added_request_vpabr = rh.request_history[SabrContextSendingPolicyAVProfile.REQUEST_ADD_CONTEXT_UPDATE].vpabr
    assert len(added_request_vpabr.streamer_context.sabr_contexts) == 1
    assert added_request_vpabr.streamer_context.sabr_contexts[0] == SabrContext(
        type=context_update_type,
        value=SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_DATA,
    )

    # Later request should remove it as per the policy that was sent by the server
    removed_request_vpabr = rh.request_history[
        SabrContextSendingPolicyAVProfile.REQUEST_DISABLE_CONTEXT_UPDATE].vpabr
    assert len(removed_request_vpabr.streamer_context.sabr_contexts) == 0

    # Should still be stored in the processor but not sent
    assert context_update_type in sabr_stream.processor.sabr_context_updates
    assert sabr_stream.processor.sabr_context_updates[
        context_update_type].value == SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_DATA
    assert sabr_stream.processor.sabr_context_updates[
        context_update_type].scope >= SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_SCOPE

    logger.debug.assert_any_call(f'Server requested to disable SABR Context Update for type {context_update_type}')

    assert len(sabr_stream.processor.sabr_contexts_to_send) == 0
