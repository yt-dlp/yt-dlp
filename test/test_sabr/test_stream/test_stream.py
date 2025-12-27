from __future__ import annotations
import io
import time
from unittest.mock import MagicMock
import protobug
import pytest
from test.test_sabr.test_stream.helpers import (
    VIDEO_PLAYBACK_USTREAMER_CONFIG,
    DEFAULT_NUM_AUDIO_SEGMENTS,
    DEFAULT_NUM_VIDEO_SEGMENTS,
    extract_rn,
    SabrRequestHandler,
    BasicAudioVideoProfile,
    SabrRedirectAVProfile,
    RequestRetryAVProfile,
    CustomAVProfile,
    assert_media_sequence_in_order,
    create_inject_read_error,
    AdWaitAVProfile,
    SabrContextSendingPolicyAVProfile,
)
from yt_dlp.extractor.youtube._streaming.sabr.exceptions import SabrStreamError
from yt_dlp.extractor.youtube._streaming.ump import UMPPartId, UMPPart
from yt_dlp.networking.exceptions import TransportError, HTTPError, RequestError

from yt_dlp.extractor.youtube._streaming.sabr.models import AudioSelector, VideoSelector
from yt_dlp.extractor.youtube._streaming.sabr.part import (
    FormatInitializedSabrPart,
    RefreshPlayerResponseSabrPart,
)
from yt_dlp.extractor.youtube._streaming.sabr.stream import SabrStream
from yt_dlp.extractor.youtube._proto.videostreaming import (
    FormatId,
    BufferedRange,
    TimeRange,
    SabrError,
    SabrContext,
)
from yt_dlp.utils import parse_qs


def setup_sabr_stream_av(
    url='https://example.com/sabr',
    sabr_response_processor=None,
    client_info=None,
    logger=None,
    **options,
):
    rh = SabrRequestHandler(sabr_response_processor=sabr_response_processor or BasicAudioVideoProfile())
    audio_selector = AudioSelector(display_name='audio')
    video_selector = VideoSelector(display_name='video')
    sabr_stream = SabrStream(
        urlopen=rh.send,
        server_abr_streaming_url=url,
        logger=logger,
        video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
        client_info=client_info,
        audio_selection=audio_selector,
        video_selection=video_selector,
        **options,
    )
    return sabr_stream, rh, (audio_selector, video_selector)


class TestStream:
    def test_sabr_audio_video(self, logger, client_info):
        # Basic successful case that both audio and video formats are requested and returned.
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )

        audio_selector, video_selector = selectors

        parts = list(sabr_stream.iter_parts())

        # 1. Check we got two format initialization metadata parts for the two formats.
        format_init_parts = [part for part in parts if isinstance(part, FormatInitializedSabrPart)]
        assert len(format_init_parts) == 2
        assert format_init_parts[0].format_id == FormatId(itag=140, lmt=123)
        assert format_init_parts[0].format_selector == audio_selector
        assert format_init_parts[1].format_id == FormatId(itag=248, lmt=456)
        assert format_init_parts[1].format_selector == video_selector

        # 2. Check that media segments are in order for both audio and video selectors.
        # note: +1 due to init segment
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        assert len(rh.request_history) == 6

    def test_sabr_basic_buffers(self, logger, client_info):
        # Check that basic audio and video buffering works as expected
        # with player time updates based on the shorter of the two streams.
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )

        list(sabr_stream.iter_parts())
        assert len(rh.request_history) == 6

        # First empty request
        assert rh.request_history[0].vpabr.buffered_ranges == []
        # Player time is at 0
        assert rh.request_history[0].vpabr.client_abr_state.player_time_ms == 0

        # Second request, first segment buffered
        assert rh.request_history[1].vpabr.buffered_ranges == [
            BufferedRange(
                format_id=FormatId(itag=140, lmt=123, xtags=None),
                start_time_ms=0, duration_ms=2000, start_segment_index=1, end_segment_index=1,
                time_range=TimeRange(start_ticks=0, duration_ticks=2000, timescale=1000)),
            BufferedRange(
                format_id=FormatId(itag=248, lmt=456, xtags=None),
                start_time_ms=0, duration_ms=1000, start_segment_index=1, end_segment_index=1,
                time_range=TimeRange(start_ticks=0, duration_ticks=1000, timescale=1000))]
        # Player time should now be at 1000ms - based on audio segment (shorter of the two)
        assert rh.request_history[1].vpabr.client_abr_state.player_time_ms == 1000

        # Second request, first segment buffered
        assert rh.request_history[2].vpabr.buffered_ranges == [
            BufferedRange(
                format_id=FormatId(itag=140, lmt=123, xtags=None),
                start_time_ms=0, duration_ms=6001, start_segment_index=1, end_segment_index=3,
                time_range=TimeRange(start_ticks=0, duration_ticks=6001, timescale=1000)),
            BufferedRange(
                format_id=FormatId(itag=248, lmt=456, xtags=None),
                start_time_ms=0, duration_ms=3001, start_segment_index=1, end_segment_index=3,
                time_range=TimeRange(start_ticks=0, duration_ticks=3001, timescale=1000))]

        assert rh.request_history[2].vpabr.client_abr_state.player_time_ms == 3001
        assert rh.request_history[3].vpabr.client_abr_state.player_time_ms == 5001
        assert rh.request_history[4].vpabr.client_abr_state.player_time_ms == 7001

        # Final request should have all but last segments buffered
        assert rh.request_history[5].vpabr.buffered_ranges == [
            BufferedRange(
                format_id=FormatId(itag=140, lmt=123, xtags=None),
                start_time_ms=0, duration_ms=10001, start_segment_index=1, end_segment_index=5,
                time_range=TimeRange(start_ticks=0, duration_ticks=10001, timescale=1000)),
            BufferedRange(
                format_id=FormatId(itag=248, lmt=456, xtags=None),
                start_time_ms=0, duration_ms=9001, start_segment_index=1, end_segment_index=9,
                time_range=TimeRange(start_ticks=0, duration_ticks=9001, timescale=1000))]
        assert rh.request_history[5].vpabr.client_abr_state.player_time_ms == 9001

    def test_sabr_request_number(self, logger, client_info):
        # Should set the "rn" query parameter correctly on each request
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        list(sabr_stream.iter_parts())
        assert len(rh.request_history) == 6
        for idx, request_details in enumerate(rh.request_history):
            expected_rn = str(idx + 1)
            actual_rn = parse_qs(request_details.request.url).get('rn', [None])[0]
            assert actual_rn == expected_rn, f'Expected rn={expected_rn}, got rn={actual_rn}'

    def test_sabr_request_headers(self, logger, client_info):
        # Should set the correct headers on each request
        sabr_stream, rh, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        list(sabr_stream.iter_parts())
        assert len(rh.request_history) == 6
        for request_details in rh.request_history:
            request = request_details.request
            assert request.headers.get('content-type') == 'application/x-protobuf'
            assert request.headers.get('accept-encoding') == 'identity'
            assert request.headers.get('accept') == 'application/vnd.yt-ump'

    def test_sabr_basic_redirect(self, logger, client_info):
        # Test successful redirect handling
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=SabrRedirectAVProfile(),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors

        assert sabr_stream.url == 'https://example.com/sabr'
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        assert len(rh.request_history) == 7
        assert rh.request_history[0].request.url == 'https://example.com/sabr?rn=1'
        assert rh.request_history[2].request.url == 'https://redirect.example.com/sabr?rn=3'
        assert rh.request_history[3].request.url == 'https://redirect.example.com/final?rn=4'
        assert rh.request_history[4].request.url == 'https://redirect.example.com/final?rn=5'
        assert sabr_stream.url == 'https://redirect.example.com/final'

    def test_sabr_reject_http_url(self, logger, client_info):
        # Do not allow HTTP URLs for server_abr_streaming_url
        rh = SabrRequestHandler(sabr_response_processor=BasicAudioVideoProfile())
        audio_selector = AudioSelector(display_name='audio')
        video_selector = VideoSelector(display_name='video')
        with pytest.raises(SabrStreamError, match='Insecure URL scheme http:// is not allowed for SABR streaming URL'):
            SabrStream(
                urlopen=rh.send,
                server_abr_streaming_url='http://example.com/sabr',
                logger=logger,
                video_playback_ustreamer_config=VIDEO_PLAYBACK_USTREAMER_CONFIG,
                client_info=client_info,
                audio_selection=audio_selector,
                video_selection=video_selector,
            )

    def test_sabr_url_update(self, logger, client_info):
        # Should allow the caller to update the URL mid-stream and use it
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors
        assert sabr_stream.url == 'https://example.com/sabr'

        # Retrieve 4 requests (based on request_history)
        parts = []
        parts_iter = sabr_stream.iter_parts()
        while len(rh.request_history) < 4:
            parts.append(next(parts_iter))
        # Update the URL
        sabr_stream.url = 'https://new.example.com/sabr'
        assert sabr_stream.url == 'https://new.example.com/sabr'
        # Continue retrieving parts
        parts.extend(list(parts_iter))
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

        assert len(rh.request_history) == 6
        assert rh.request_history[0].request.url == 'https://example.com/sabr?rn=1'
        assert rh.request_history[1].request.url == 'https://example.com/sabr?rn=2'
        assert rh.request_history[2].request.url == 'https://example.com/sabr?rn=3'
        assert rh.request_history[3].request.url == 'https://example.com/sabr?rn=4'
        assert rh.request_history[4].request.url == 'https://new.example.com/sabr?rn=5'
        assert rh.request_history[5].request.url == 'https://new.example.com/sabr?rn=6'
        assert sabr_stream.url == 'https://new.example.com/sabr'

    @pytest.mark.parametrize(
        'bad_url',
        [None, '', 'bad-url%', 'http://insecure.example.com', 'file:///etc/passwd', 'https://example.org/sabr'],
        ids=['none', 'empty', 'malformed', 'insecure', 'file scheme', 'different domain'])
    def test_sabr_update_url_invalid(self, logger, client_info, bad_url):
        # Should reject invalid URLs relative to the current URL when updating sabr_stream.url
        sabr_stream, _, _ = setup_sabr_stream_av(
            sabr_response_processor=BasicAudioVideoProfile(),
            client_info=client_info,
            logger=logger,
        )
        assert sabr_stream.url == 'https://example.com/sabr'

        with pytest.raises(SabrStreamError, match='Invalid SABR streaming URL'):
            sabr_stream.url = bad_url

        assert sabr_stream.url == 'https://example.com/sabr'

    @pytest.mark.parametrize(
        'bad_url',
        [None, '', 'bad-url%', 'http://insecure.example.com', 'file:///etc/passwd', 'https://example.org/sabr'],
        ids=['none', 'empty', 'malformed', 'insecure', 'file scheme', 'different domain'])
    def test_sabr_process_redirect_invalid_url(self, logger, client_info, bad_url):
        # Should ignore an invalid redirect URl and continue with the current URL
        sabr_stream, rh, selectors = setup_sabr_stream_av(
            sabr_response_processor=SabrRedirectAVProfile({'redirects': {2: {'url': bad_url, 'replace': True}}}),
            client_info=client_info,
            logger=logger,
        )
        audio_selector, video_selector = selectors
        parts = list(sabr_stream.iter_parts())
        assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
        assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)
        assert len(rh.request_history) == 7
        assert sabr_stream.url == 'https://example.com/sabr'
        logger.warning.assert_any_call(f'Server requested to redirect to an invalid URL: {bad_url}')

    def test_sabr_set_live_from_url_source(self, logger, client_info):
        # Should set is_live to True based on source URL parameter
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url='https://example.com/sabr?source=yt_live_broadcast',
        )
        assert sabr_stream.url == 'https://example.com/sabr?source=yt_live_broadcast'
        assert sabr_stream.processor.is_live is True

    def test_sabr_nonlive_ignore_broadcast_id_update(self, logger, client_info):
        # Should ignore broadcast_id updates in URL when non-live
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url='https://example.com/sabr?id=1',
        )

        assert sabr_stream.processor.is_live is False
        sabr_stream.url = 'https://example.com/sabr?id=2'
        assert sabr_stream.processor.is_live is False
        assert sabr_stream.url == 'https://example.com/sabr?id=2'

    @pytest.mark.parametrize('post_live', [True, False], ids=['post_live=True', 'post_live=False'])
    def test_sabr_live_error_on_broadcast_id_update(self, logger, client_info, post_live):
        # Should raise an error if broadcast_id changes for live stream. Post live flag should not affect this.
        sabr_stream, _, _ = setup_sabr_stream_av(
            client_info=client_info,
            logger=logger,
            url='https://example.com/sabr?source=yt_live_broadcast&id=1',
            post_live=post_live,
        )

        assert sabr_stream.processor.is_live is True
        with pytest.raises(SabrStreamError, match=r'Broadcast ID changed from 1 to 2\. The download will need to be restarted\.'):
            sabr_stream.url = 'https://example.com/sabr?source=yt_live_broadcast&id=2'

    class TestExpiry:
        def test_sabr_expiry_refresh_player_response(self, logger, client_info):
            # Should yield a refresh player response part if within the expiry time
            # This should occur before the next request
            expires_at = int(time.time() + 30)  # 30 seconds from now
            sabr_stream, rh, _ = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                url=f'https://example.com/sabr?expire={int(expires_at)}',
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
            logger.debug.assert_called_with(r'Requesting player response refresh as SABR URL is due to expire within 60 seconds')

        def test_sabr_expiry_threshold_sec(self, logger, client_info):
            # Should use the configured expiry threshold seconds when determining to refresh player response
            expires_at = int(time.time() + 100)  # 100 seconds from now
            sabr_stream, rh, _ = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                url=f'https://example.com/sabr?expire={int(expires_at)}',
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
            logger.debug.assert_called_with(r'Requesting player response refresh as SABR URL is due to expire within 120 seconds')

        def test_sabr_no_expiry_in_url(self, logger, client_info):
            # Should not yield a refresh player response part if no expiry in URL
            # It should log a warning about missing expiry
            sabr_stream, _, _ = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                url='https://example.com/sabr',
            )
            parts = list(sabr_stream.iter_parts())
            assert all(not isinstance(part, RefreshPlayerResponseSabrPart) for part in parts)
            logger.warning.assert_called_with('No expiry timestamp found in SABR URL. Will not be able to refresh.', once=True)

        def test_sabr_not_expired(self, logger, client_info):
            # Should not yield a refresh player response part if not within the expiry threshold
            expires_at = int(time.time() + 300)  # 5 minutes from now
            sabr_stream, _, _ = setup_sabr_stream_av(
                client_info=client_info,
                logger=logger,
                url=f'https://example.com/sabr?expire={int(expires_at)}',
                # By default, expiry threshold is 60 seconds
            )
            parts = list(sabr_stream.iter_parts())
            assert all(not isinstance(part, RefreshPlayerResponseSabrPart) for part in parts)

    class TestRequestRetries:
        def test_sabr_retry_on_transport_error(self, logger, client_info):
            # Should retry on TransportError occurring during request
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # Find the first request that recorded an error
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)

            request = rh.request_history[i_err]
            assert isinstance(request.error, TransportError)
            assert request.error.cause == 'simulated transport error'

            # There should be a retry request recorded immediately after the error
            retried_request = rh.request_history[i_err + 1]
            assert retried_request.error is None

            # The video_playback_abr_request should be the same for both requests - no changes in state (e.g playback time)
            assert request.request.data == retried_request.request.data

            # Should log the retry attempt
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')

        def test_sabr_retry_on_http_5xx(self, logger, client_info):
            # Should retry on HTTP 5xx errors
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'http', 'status': 500, 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )

            parts = list(sabr_stream.iter_parts())
            audio_selector, video_selector = selectors
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # Find the first request that recorded an error
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)

            request = rh.request_history[i_err]
            assert isinstance(request.error, HTTPError)
            assert request.error.status == 500

            # There should be a retry request recorded immediately after the error
            retried_request = rh.request_history[i_err + 1]
            assert retried_request.error is None
            # The video_playback_abr_request should be the same for both requests - no changes in state (e.g playback time)
            assert request.request.data == retried_request.request.data
            # Should log the retry attempt
            logger.warning.assert_any_call('[sabr] Got error: HTTP Error 500: Internal Server Error. Retrying (1/10)...')

        def test_sabr_no_retry_on_http_4xx(self, logger, client_info):
            # Should NOT retry on HTTP 4xx errors and should raise SabrStreamError
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'http', 'status': 404, 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )

            with pytest.raises(SabrStreamError, match=r'404'):
                list(sabr_stream.iter_parts())

            # Ensure the failing request was recorded and no retry was attempted
            assert len(rh.request_history) >= 1
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)
            assert isinstance(rh.request_history[i_err].error, HTTPError)
            assert rh.request_history[i_err].error.status == 404
            assert len(rh.request_history) == i_err + 1

        def test_sabr_no_retry_on_request_error(self, logger, client_info):
            # Should NOT retry on RequestError (non-network error)
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'request', 'rn': [2]}),
                client_info=client_info,
                logger=logger,
            )
            # We don't currently wrap in SabrStreamError as could be client issue
            with pytest.raises(RequestError, match='simulated request error'):
                list(sabr_stream.iter_parts())

            # Ensure the failing request was recorded and no retry was attempted
            assert len(rh.request_history) >= 1
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)
            assert isinstance(rh.request_history[i_err].error, RequestError)
            assert len(rh.request_history) == i_err + 1

        def test_sabr_multiple_retries(self, logger, client_info):
            # Should retry multiple times on consecutive errors
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 3, 4]}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # Find the requests that recorded errors
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 3
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # There should be a retry request recorded immediately after the three errors
            last_error_request = error_requests[-1]
            retried_request = rh.request_history[rh.request_history.index(last_error_request) + 1]
            assert retried_request.error is None
            # The video_playback_abr_request should be the same for all requests - no changes in state (e.g playback time)
            assert error_requests[0].request.data == retried_request.request.data

            # Should log each retry attempt
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (2/10)...')
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (3/10)...')

        def test_sabr_reset_retry_counter(self, logger, client_info):
            # Should reset the retry counter after a successful request
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 4]}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # Find the requests that recorded errors
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 2
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # There should be a retry request recorded immediately after each error
            first_error_request = error_requests[0]
            first_retried_request = rh.request_history[rh.request_history.index(first_error_request) + 1]
            assert first_retried_request.error is None
            second_error_request = error_requests[1]
            second_retried_request = rh.request_history[rh.request_history.index(second_error_request) + 1]
            assert second_retried_request.error is None

            # Should log each retry attempt with correct counts
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/10)...')

        def test_sabr_exceed_max_retries(self, logger, client_info):
            # Should raise SabrStreamError after exceeding max retries
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 15))}),
                client_info=client_info,
                logger=logger,
            )

            with pytest.raises(TransportError, match='simulated transport error'):
                list(sabr_stream.iter_parts())

            # There should be max_retry + 1 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 11  # Default max retries is 10
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # Should log each retry attempt
            for i in range(1, 11):
                logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

        def test_sabr_http_retries_option(self, logger, client_info):
            # Should respect the http_retries option for max retries
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 8))}),
                client_info=client_info,
                logger=logger,
                http_retries=5,
            )

            with pytest.raises(TransportError, match='simulated transport error'):
                list(sabr_stream.iter_parts())

            # There should be http_retries + 1 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 6  # http_retries is set to 5
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # Should log each retry attempt
            for i in range(1, 6):
                logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/5)...')

        def test_sabr_http_retry_sleep_func(self, logger, client_info):
            # Should call the retry_sleep_func between retries to get the sleep duration
            # For this test, we want to return 0.001 as the sleep
            sleep_mock = MagicMock()
            sleep_mock.side_effect = lambda n: 0.001

            sabr_stream, _, __ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 3]}),
                client_info=client_info,
                logger=logger,
                http_retries=3,
                retry_sleep_func=sleep_mock,
            )
            # Should complete successfully
            list(sabr_stream.iter_parts())
            # sleep_mock should be called 2 times (for the two retries)
            assert sleep_mock.call_count == 2
            sleep_mock.assert_any_call(n=0)
            sleep_mock.assert_any_call(n=1)

            # Check logs for retry attempts
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (1/3)...')
            logger.warning.assert_any_call('[sabr] Got error: simulated transport error. Retrying (2/3)...')
            # Should log the sleep
            logger.info.assert_any_call('Sleeping 0.00 seconds ...')

        def test_sabr_expiry_on_retry(self, logger, client_info):
            # Should check for expiry before retrying and yield RefreshPlayerResponseSabrPart if within threshold
            expires_at = int(time.time() + 30)  # 30 seconds from now
            sabr_stream, _, __ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(7))}),
                client_info=client_info,
                logger=logger,
                url=f'https://example.com/sabr?expire={int(expires_at)}',
                http_retries=5,
                # By default, expiry threshold is 60 seconds
            )

            # Retrieve all parts until we fail
            parts = []
            with pytest.raises(TransportError, match='simulated transport error'):
                for part in sabr_stream.iter_parts():
                    parts.append(part)

            # Should get 6 RefreshPlayerResponseSabrPart parts before failing
            # (If the check was AFTER the retry was triggered, we would only get 1)
            refresh_parts = [part for part in parts if isinstance(part, RefreshPlayerResponseSabrPart)]
            assert len(refresh_parts) == 6

        def test_sabr_increment_rn_on_retry(self, logger, client_info):
            # Should increment the "rn" parameter on each retry request
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': [2, 3, 4]}),
                client_info=client_info,
                logger=logger,
            )

            # Should complete successfully
            list(sabr_stream.iter_parts())

            # Find the requests that recorded errors
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 3

            # Check that the "rn" parameter increments correctly
            for i, request_details in enumerate(rh.request_history):
                expected_rn = i + 1
                actual_rn = extract_rn(request_details.request.url)
                assert actual_rn == expected_rn, f'Expected rn={expected_rn}, got rn={actual_rn}'

    class TestResponseRetries:

        def test_sabr_retry_on_response_error(self, logger, client_info):
            # Should retry on SabrResponseError occurring during response processing
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': lambda parts, vpabr, url, request_number: [TransportError('simulated SABR response error')] if request_number == 2 else parts}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # Find the first request that recorded an error
            i_err = next(i for i, d in enumerate(rh.request_history) if d.error is not None)

            request = rh.request_history[i_err]
            assert isinstance(request.error, TransportError)
            assert request.error.msg == 'simulated SABR response error'

            # There should be a retry request recorded immediately after the error
            retried_request = rh.request_history[i_err + 1]
            assert retried_request.error is None

            # The video_playback_abr_request should be the same for both requests - no changes in state (e.g playback time)
            # (as the error was during before any parts were processed)
            assert request.request.data == retried_request.request.data

            # Should log the retry attempt
            logger.warning.assert_any_call('[sabr] Got error: simulated SABR response error. Retrying (1/10)...')

        def test_sabr_retry_read_failure_media_part(self, logger, client_info):
            # Should retry if a TransportError occurs while reading a media part
            inject_read_error = create_inject_read_error([2], part_id=UMPPartId.MEDIA)

            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': inject_read_error}),
                client_info=client_info,
                logger=logger,
            )

            audio_selector, video_selector = selectors

            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1, allow_retry=True)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1, allow_retry=True)

            # As this is the first MEDIA part in the response,
            # the playback time should NOT have advanced, and buffered ranges should be the same.

            request = rh.request_history[1]  # The request that had the read error
            retried_request = rh.request_history[2]  # followup retried request
            assert request.request.data == retried_request.request.data

            # TODO: currently raises a partial segments warning, this is incorrect!
            logger.warning.assert_any_call('[sabr] Got error: simulated read error. Retrying (1/10)...')

        def test_sabr_retry_failure_nth_media_part(self, logger, client_info):
            # Should retry if a TransportError occurs while reading the Nth media part
            # In this case, the first media part should be processed successfully,
            # so the playback time should NOT be advanced, but buffered ranges should have been updated.
            inject_read_error = create_inject_read_error([2], part_id=UMPPartId.MEDIA, occurance=2)
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': inject_read_error}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1, allow_retry=True)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1, allow_retry=True)
            # The playback time and buffered ranges should have advanced after the first media part
            request = rh.request_history[1]  # The request that had the read error
            retried_request = rh.request_history[2]  # followup retried request
            # The playback time in the retried request should be advanced by the duration of one media part
            original_vpabr = request.vpabr
            retried_vpabr = retried_request.vpabr

            # Player time should be the same as original
            assert retried_vpabr.client_abr_state.player_time_ms == original_vpabr.client_abr_state.player_time_ms

            # ONE of the buffered ranges should be one segment ahead (as these are updated after a media part is processed)
            matches = 0
            for br in original_vpabr.buffered_ranges:
                # find matching buffered range in retried_vpabr by format_id
                br_retried = next((r for r in retried_vpabr.buffered_ranges if r.format_id == br.format_id), None)
                assert br_retried is not None
                # The end of the buffered range should be advanced by one segment duration
                if br_retried.end_segment_index == br.end_segment_index + 1:
                    matches += 1
            assert matches == 1, 'Expected one buffered range to be advanced by one segment after retrying Nth media part read failure'

            # TODO: currently raises a partial segments warning, this is incorrect!
            logger.warning.assert_any_call('[sabr] Got error: simulated read error. Retrying (1/10)...')

        def test_sabr_retry_on_response_read_failure_end(self, logger, client_info):
            # Should retry if a TransportError occurs after we have read all segments in the response and video
            # We can simulate this by adding a informational part at the end that fails to read
            def inject_read_error(parts, vpabr, url, request_number):
                if request_number != 6:
                    return parts
                parts.append(UMPPart(
                    part_id=UMPPartId.SNACKBAR_MESSAGE,
                    size=0,
                    data=io.BytesIO(b''),
                ))
                return create_inject_read_error([6], part_id=UMPPartId.SNACKBAR_MESSAGE, occurance=1)(parts, vpabr, url, request_number)

            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': inject_read_error}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors
            parts = list(sabr_stream.iter_parts())
            # Should not be getting any retried segments here as the error is after all media parts
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1, allow_retry=False)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1, allow_retry=False)

            assert len(rh.request_history) == 7  # Original + 1 retried request
            # The playback time and buffered ranges should have advanced
            request = rh.request_history[5]  # The request that had the read error
            retried_request = rh.request_history[6]  # followup retried request
            # The playback time in the retried request should be advanced by the duration of one media part
            original_vpabr = request.vpabr
            retried_vpabr = retried_request.vpabr

            # Player time should be the same as original
            assert retried_vpabr.client_abr_state.player_time_ms == original_vpabr.client_abr_state.player_time_ms

            # At least ONE of the buffered ranges should be one segment ahead (as these are updated after a media part is processed)
            matches = 0
            for br in original_vpabr.buffered_ranges:
                # find matching buffered range in retried_vpabr by format_id
                br_retried = next((r for r in retried_vpabr.buffered_ranges if r.format_id == br.format_id), None)
                assert br_retried is not None
                # The end of the buffered range should be advanced by one segment duration
                if br_retried.end_segment_index > br.end_segment_index:
                    matches += 1
            assert matches >= 1, 'Expected at least one buffered range to be advanced by one segment after retrying Nth media part read failure'

            logger.warning.assert_any_call('[sabr] Got error: simulated read error. Retrying (1/10)...')

    class TestSabrErrorRetries:
        def test_sabr_retry_on_sabr_error_part(self, logger, client_info):
            def sabr_error_injector(parts, vpabr, url, request_number):
                if request_number == 2:
                    message = protobug.dumps(SabrError(action=1, type='simulated SABR error'))

                    # Insert after the first MEDIA_END. SabrStream should stop processing the response at this point.
                    for i, p in enumerate(parts):
                        if p.part_id == UMPPartId.MEDIA_END:
                            parts.insert(i + 1, UMPPart(
                                part_id=UMPPartId.SABR_ERROR,
                                size=len(message),
                                data=io.BytesIO(message),
                            ))
                            break

                return parts

            sabr_stream, _, selectors = setup_sabr_stream_av(
                sabr_response_processor=CustomAVProfile({'custom_parts_function': sabr_error_injector}),
                client_info=client_info,
                logger=logger,
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)
            # xxx: not recorded as an error in the request history as SabrError is part of normal processing.
            # We rely on assert_media_sequence_in_order to ensure all parts were eventually retrieved and the logs for retry attempts.
            logger.warning.assert_any_call("[sabr] Got error: SABR Protocol Error: SabrError(type='simulated SABR error', action=1, error=None). Retrying (1/10)...")

    class TestGVSFallbackRetries:
        def test_sabr_gvs_fallback_after_8_retries(self, logger, client_info):
            # Should fallback to next gvs server after max retries exceeded
            sabr_stream, rh, selectors = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 10))}),
                client_info=client_info,
                logger=logger,
                url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6',
            )
            audio_selector, video_selector = selectors

            # Should complete successfully
            parts = list(sabr_stream.iter_parts())
            assert_media_sequence_in_order(parts, audio_selector, DEFAULT_NUM_AUDIO_SEGMENTS + 1)
            assert_media_sequence_in_order(parts, video_selector, DEFAULT_NUM_VIDEO_SEGMENTS + 1)

            # There should be 8 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 8
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # Check that the host was switched after 8 retries
            last_error_request = error_requests[-1]
            for following_request in rh.request_history[rh.request_history.index(last_error_request) + 1:]:
                # TODO: this should be rr3, gvs fallback function needs fixing
                assert 'rr1---sn-7654321.googlevideo.com' in following_request.request.url
                assert 'fallback_count=1' in following_request.request.url

            # Check request before fallback
            assert 'rr6---sn-6942067.googlevideo.com' in last_error_request.request.url

            # Should have 8 fallback attempts logged
            for i in range(1, 9):
                logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

            logger.warning.assert_any_call('Falling back to host rr1---sn-7654321.googlevideo.com')

        def test_sabr_gvs_fallback_multiple_hosts(self, logger, client_info):
            # Should keep falling back to next gvs server until default max total attempts exceeded
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 15))}),
                client_info=client_info,
                logger=logger,
                url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6',
            )

            with pytest.raises(TransportError, match='simulated transport error'):
                list(sabr_stream.iter_parts())

            # There should be 11 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 11
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'
            # Check that the host was switched after each fallback threshold

            # TODO: fix these hosts, gvs fallback function needs fixing
            retry_request_one = error_requests[8]  # first fallback
            assert 'rr1---sn-7654321.googlevideo.com' in retry_request_one.request.url
            assert 'fallback_count=1' in retry_request_one.request.url
            logger.warning.assert_any_call('Falling back to host rr1---sn-7654321.googlevideo.com')

            retry_request_two = error_requests[9]  # second fallback
            assert 'rr4---sn-7654321.googlevideo.com' in retry_request_two.request.url
            assert 'fallback_count=2' in retry_request_two.request.url
            logger.warning.assert_any_call('Falling back to host rr4---sn-7654321.googlevideo.com')

            retry_request_three = error_requests[10]  # third fallback before giving up
            assert 'rr3---sn-6942067.googlevideo.com' in retry_request_three.request.url
            assert 'fallback_count=3' in retry_request_three.request.url
            logger.warning.assert_any_call('Falling back to host rr3---sn-6942067.googlevideo.com')

        def test_sabr_gvs_fallback_threshold_option(self, logger, client_info):
            # Should respect the host_fallback_threshold option for retries before fallback
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 5))}),
                client_info=client_info,
                logger=logger,
                url='https://rr6---sn-6942067.googlevideo.com?mn=sn-6942067,sn-7654321&fvip=3&mvi=6',
                host_fallback_threshold=3,
            )

            # Should complete successfully
            list(sabr_stream.iter_parts())

            # There should be 3 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 3
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # Check that the host was switched after 3 retries
            last_error_request = error_requests[-1]
            for following_request in rh.request_history[rh.request_history.index(last_error_request) + 1:]:
                # TODO: this should be rr3, gvs fallback function needs fixing
                assert 'rr1---sn-7654321.googlevideo.com' in following_request.request.url
                assert 'fallback_count=1' in following_request.request.url

            # Check request before fallback
            assert 'rr6---sn-6942067.googlevideo.com' in last_error_request.request.url

            # Should have 4 fallback attempts logged
            for i in range(1, 4):
                logger.warning.assert_any_call(f'[sabr] Got error: simulated transport error. Retrying ({i}/10)...')

            logger.warning.assert_any_call('Falling back to host rr1---sn-7654321.googlevideo.com')

        def test_sabr_gvs_fallback_no_fallback_available(self, logger, client_info):
            # Should not fallback if there are no fallback options available
            sabr_stream, rh, _ = setup_sabr_stream_av(
                sabr_response_processor=RequestRetryAVProfile({'mode': 'transport', 'rn': list(range(2, 15))}),
                client_info=client_info,
                logger=logger,
                url='https://rr6---sn-6942067.googlevideo.com',
            )

            with pytest.raises(TransportError, match='simulated transport error'):
                list(sabr_stream.iter_parts())

            # There should be 11 error requests recorded
            error_requests = [d for d in rh.request_history if d.error is not None]
            assert len(error_requests) == 11
            for request in error_requests:
                assert isinstance(request.error, TransportError)
                assert request.error.cause == 'simulated transport error'

            # All should have the same host
            for request in error_requests:
                assert 'rr6---sn-6942067.googlevideo.com' in request.request.url

            assert not any('Falling back to host' in call.args[0] for call in logger.warning.call_args_list)
            assert logger.debug.assert_any_call('No more fallback hosts available')

    class TestAdWait:
        def test_sabr_ad_wait(self, logger, client_info):
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
            logger.warning.assert_any_call(
                'Received a SABR Context Update. YouTube is likely trying to force ads on the client. This may cause issues with playback.')

            # Second request should be sending the ad wait sabr context update
            ad_wait_request_vpabr = rh.request_history[1].vpabr
            assert len(ad_wait_request_vpabr.streamer_context.sabr_contexts) == 1
            assert ad_wait_request_vpabr.streamer_context.sabr_contexts[0] == SabrContext(
                type=AdWaitAVProfile.CONTEXT_UPDATE_TYPE,
                value=AdWaitAVProfile.CONTEXT_UPDATE_DATA,
            )

            # SabrStream rounds up the wait time to nearest second
            logger.info.assert_any_call('The server is requiring yt-dlp to wait 1 seconds before continuing due to ad enforcement')

            assert AdWaitAVProfile.CONTEXT_UPDATE_TYPE in sabr_stream.processor.sabr_context_updates
            assert sabr_stream.processor.sabr_context_updates[5].value == AdWaitAVProfile.CONTEXT_UPDATE_DATA
            assert sabr_stream.processor.sabr_context_updates[5].scope >= AdWaitAVProfile.CONTEXT_UPDATE_SCOPE
            assert AdWaitAVProfile.CONTEXT_UPDATE_TYPE in sabr_stream.processor.sabr_contexts_to_send

        def test_sabr_sending_policy(self, logger, client_info):
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
            removed_request_vpabr = rh.request_history[SabrContextSendingPolicyAVProfile.REQUEST_DISABLE_CONTEXT_UPDATE].vpabr
            assert len(removed_request_vpabr.streamer_context.sabr_contexts) == 0

            # Should still be stored in the processor but not sent
            assert context_update_type in sabr_stream.processor.sabr_context_updates
            assert sabr_stream.processor.sabr_context_updates[context_update_type].value == SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_DATA
            assert sabr_stream.processor.sabr_context_updates[context_update_type].scope >= SabrContextSendingPolicyAVProfile.CONTEXT_UPDATE_SCOPE

            logger.debug.assert_any_call(f'Server requested to disable SABR Context Update for type {context_update_type}')

            assert len(sabr_stream.processor.sabr_contexts_to_send) == 0
