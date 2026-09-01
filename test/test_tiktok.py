#!/usr/bin/env python3

import unittest
from types import SimpleNamespace

from yt_dlp.extractor._tiktok import (
    TikTokWebpagePolicy,
    get_tiktok_webpage_policy,
    get_video_data,
    get_video_detail,
    get_video_status,
    has_playable_video,
)
from yt_dlp.extractor.tiktok import TikTokBaseIE
from yt_dlp.utils import ExtractorError


class TestTikTokWebpagePolicy(unittest.TestCase):
    def test_success_promotes_target_and_failure_demotes_target(self):
        policy = TikTokWebpagePolicy(('first', 'second', 'third'))

        policy.succeeded('third')
        self.assertEqual(policy.candidates(), ('third', 'first', 'second'))

        policy.failed('third')
        self.assertEqual(policy.candidates(), ('first', 'second', 'third'))

    def test_new_reflow_schema_is_playable(self):
        universal_data = {
            'webapp.reflow.video.detail': {
                'itemInfo': {'itemStruct': {'video': {'playAddr': 'https://example.com/video.mp4'}}},
            },
        }
        detail = get_video_detail(universal_data)

        self.assertTrue(has_playable_video(detail))
        self.assertEqual(get_video_data(detail)['video']['playAddr'], 'https://example.com/video.mp4')

    def test_detail_without_play_address_is_not_playable(self):
        detail = {'itemInfo': {'itemStruct': {'video': {}}}}

        self.assertFalse(has_playable_video(detail))

    def test_malformed_video_detail_is_not_exposed_to_extractor(self):
        self.assertEqual(get_video_detail({'webapp.reflow.video.detail': []}), {})

    def test_video_status_is_normalized(self):
        self.assertEqual(get_video_status({'statusCode': '10216'}), 10216)

    def test_policy_is_reused_per_downloader_instance(self):
        class FakeYDL:
            def _get_available_impersonate_targets(self):
                return [('first', 'test'), ('second', 'test')]

        ydl = FakeYDL()
        first_policy = get_tiktok_webpage_policy(ydl)
        first_policy.succeeded('second')

        self.assertIs(get_tiktok_webpage_policy(ydl), first_policy)
        self.assertEqual(first_policy.candidates(), ('second', 'first'))


class TestTikTokWebpageFallback(unittest.TestCase):
    class FakeYDL:
        def _get_available_impersonate_targets(self):
            return [('first', 'test'), ('second', 'test')]

    class FakeTikTokIE(TikTokBaseIE):
        def __init__(self, downloader, *, network_error=False, status_code=0):
            super().__init__(downloader)
            self.calls = []
            self.network_error = network_error
            self.status_code = status_code
            self.warnings = []

        def _download_webpage_handle(self, url, video_id, note, **kwargs):
            self.calls.append((kwargs['impersonate'], note))
            if self.network_error:
                raise ExtractorError('network failed')
            return ('challenge' if note != 'Downloading webpage' else 'initial', SimpleNamespace(
                url=url, extensions={'impersonate': kwargs['impersonate']}))

        def _get_universal_data(self, webpage, video_id):
            return ({
                'webapp.reflow.video.detail': {
                    'statusCode': self.status_code,
                    'itemInfo': {'itemStruct': {'video': {'playAddr': 'https://example.com/video.mp4'}}} if self.status_code == 0 else {},
                },
            } if webpage == 'challenge' or self.status_code else {})

        def _solve_challenge_and_set_cookies(self, webpage):
            return ()

        def write_debug(self, message):
            pass

        def report_warning(self, message, **kwargs):
            self.warnings.append(message)

    def test_challenge_is_solved_with_the_same_target(self):
        ie = self.FakeTikTokIE(self.FakeYDL())

        video_data, status = ie._extract_web_data_and_status('https://example.com/video', 'video')

        self.assertEqual(status, 0)
        self.assertTrue(video_data['video']['playAddr'])
        self.assertEqual(ie.calls, [('first', 'Downloading webpage'), ('first', 'Downloading webpage with challenge cookie')])

    def test_nonfatal_network_failure_reports_warning(self):
        ie = self.FakeTikTokIE(self.FakeYDL(), network_error=True)

        self.assertEqual(ie._extract_web_data_and_status('https://example.com/video', 'video', fatal=False), ({}, -1))
        self.assertEqual(ie.warnings, ['network failed'])

    def test_terminal_status_bypasses_fallback(self):
        ie = self.FakeTikTokIE(self.FakeYDL(), status_code=10216)

        self.assertEqual(ie._extract_web_data_and_status('https://example.com/video', 'video'), ({}, 10216))
        self.assertEqual(ie.calls, [('first', 'Downloading webpage')])


if __name__ == '__main__':
    unittest.main()
