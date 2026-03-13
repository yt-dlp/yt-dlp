from __future__ import annotations
import io
import protobug
from yt_dlp.extractor.youtube._streaming.ump import UMPPart, UMPPartId

from test.test_sabr.test_stream.helpers import (
    DEFAULT_NUM_AUDIO_SEGMENTS,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    assert_media_sequence_in_order,
    AdWaitAVProfile,
    SabrContextSendingPolicyAVProfile,
    mock_time,
    setup_sabr_stream_av, LiveAVProfile, VALID_LIVE_URL,
)

from yt_dlp.extractor.youtube._proto.videostreaming import SabrContext, Cuepoint, CuepointType, AdCuepointConfig, SabrSeek
from yt_dlp.extractor.youtube._proto.videostreaming.cuepoint_list import CuepointInfo, CuepointEvent, TrackType, CuepointList


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


def generate_cuepoint_info(identifier, event, track_type):
    # Currently we ignore any of the duration info, but could be something to consider at a later date
    return CuepointInfo(
        cuepoint=Cuepoint(
            type=CuepointType.CUEPOINT_TYPE_AD,
            event=event,
            identifier=identifier),
        track_type=track_type,
    )


class TestLiveCuepointAds:

    @mock_time
    def test_cuepoint_identifier_states(self, logger, client_info):
        # Should send cuepoint identifiers during the applicable states
        identifier = 'test_identifier'
        cuepoints = {
            1: [
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_PREDICT_START, track_type=TrackType.TRACK_TYPE_AUDIO),
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_PREDICT_START, track_type=TrackType.TRACK_TYPE_VIDEO),
            ],
            2: [
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_START, track_type=TrackType.TRACK_TYPE_AUDIO),
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_START, track_type=TrackType.TRACK_TYPE_VIDEO),
            ],
            # should continue to send if cuepoint_info not provided
            4: [
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_CONTINUE, track_type=TrackType.TRACK_TYPE_AUDIO),
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_CONTINUE, track_type=TrackType.TRACK_TYPE_VIDEO),
            ],
            5: [
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_INSERTION, track_type=TrackType.TRACK_TYPE_AUDIO),
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_INSERTION, track_type=TrackType.TRACK_TYPE_VIDEO),
            ],
            6: [
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_STOP, track_type=TrackType.TRACK_TYPE_AUDIO),
                generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_STOP, track_type=TrackType.TRACK_TYPE_VIDEO),
            ],
        }

        def insert_cuepoints(parts, vpabr, url, request_number):
            if request_number in cuepoints:
                for cuepoint_info in cuepoints[request_number]:
                    payload = protobug.dumps(CuepointList(cuepoint_info=[cuepoint_info]))
                    parts.append(
                        UMPPart(
                            part_id=UMPPartId.CUEPOINT_LIST,
                            data=io.BytesIO(payload),
                            size=len(payload),
                        ),
                    )
            return parts

        total_segments = 10
        segment_target_duration_ms = 2000
        dvr_segments = 9
        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': dvr_segments,
            'custom_parts_function': insert_cuepoints,
        })

        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )

        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, total_segments)
        assert_media_sequence_in_order(parts, video_selector, total_segments)

        # First request should not include cuepoint identifier
        first_request_vpabr = rh.request_history[0].vpabr
        assert len(first_request_vpabr.ad_cuepoints) == 0

        # Requests 2-5 should include the cuepoint identifier in the sabr context
        for request_number in range(2, 6):
            request_vpabr = rh.request_history[request_number].vpabr
            assert len(request_vpabr.ad_cuepoints) == 1
            assert isinstance(request_vpabr.ad_cuepoints[0], AdCuepointConfig)
            assert request_vpabr.ad_cuepoints[0].cuepoint_id == identifier
            assert request_vpabr.ad_cuepoints[0].magic_value == 11

        # Request 5 and onwards should not include the cuepoint identifier
        for request in rh.request_history[6:]:
            assert len(request.vpabr.ad_cuepoints) == 0

        # Check one of the SABR State logs include acp:1 (ad cue point number0
        assert any(
            'acp:1' in call.args[0] for call in logger.debug.call_args_list
            if 'SABR State' in call.args[0])

    @mock_time
    def test_clear_cuepoint_on_sabr_seek(self, logger, client_info):
        # Should clear cuepoint identifier on seek

        total_segments = 10
        segment_target_duration_ms = 2000

        identifier = 'test_identifier'

        seek_ms = segment_target_duration_ms * 4

        def insert_cuepoints_and_seek(parts, vpabr, url, request_number):

            if request_number == 1:
                payload = protobug.dumps(CuepointList(
                    cuepoint_info=[generate_cuepoint_info(identifier, CuepointEvent.CUEPOINT_EVENT_START, track_type=TrackType.TRACK_TYPE_AUDIO)]))
                parts.append(
                    UMPPart(
                        part_id=UMPPartId.CUEPOINT_LIST,
                        data=io.BytesIO(payload),
                        size=len(payload),
                    ),
                )

            if request_number == 2:
                sabr_seek = protobug.dumps(SabrSeek(
                    seek_time_ticks=seek_ms,
                    timescale=1000,
                ))
                parts.append(UMPPart(
                    part_id=UMPPartId.SABR_SEEK,
                    size=len(sabr_seek),
                    data=io.BytesIO(sabr_seek),
                ))
            return parts

        profile = LiveAVProfile({
            'total_segments': total_segments,
            'segment_target_duration_ms': segment_target_duration_ms,
            'dvr_segments': 9,
            'custom_parts_function': insert_cuepoints_and_seek,
        })

        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=profile,
            client_info=client_info,
            logger=logger,
            url=VALID_LIVE_URL,
            live_segment_target_duration_sec=segment_target_duration_ms // 1000,
        )

        list(sabr_stream.iter_parts())

        # First request should not include cuepoint identifier
        first_request_vpabr = rh.request_history[0].vpabr
        assert len(first_request_vpabr.ad_cuepoints) == 0

        # Second request should include the cuepoint identifier in the sabr context
        second_request_vpabr = rh.request_history[1].vpabr
        assert len(second_request_vpabr.ad_cuepoints) == 1
        assert isinstance(second_request_vpabr.ad_cuepoints[0], AdCuepointConfig)
        assert second_request_vpabr.ad_cuepoints[0].cuepoint_id == identifier
        assert second_request_vpabr.ad_cuepoints[0].magic_value == 11

        # Third request should be after the seek and should not include the cuepoint identifier
        third_request_vpabr = rh.request_history[2].vpabr
        assert len(third_request_vpabr.ad_cuepoints) == 0
        assert third_request_vpabr.client_abr_state.player_time_ms == seek_ms

        # All following requests should also not include the cuepoint identifier
        for request in rh.request_history[3:]:
            assert len(request.vpabr.ad_cuepoints) == 0
