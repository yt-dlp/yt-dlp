#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import FakeYDL
from yt_dlp.extractor.mediaklikk import MediaKlikkAudioIE, MediaKlikkIE
from yt_dlp.utils import ExtractorError

AUDIO_URL = 'https://mediaklikk.hu/audio/kossuth-radio/2026/11/24/17-30/esti-kronika/'
VIDEO_URL = 'https://mediaklikk.hu/video/2026/11/24/hirado-2026-november-21-12-00'

AUDIO_PAGE = '''<html><head><meta property="og:title" content="Esti krónika"/></head><body>
<h2 class="aod_title">Esti krónika</h2>
<div class="playButton playback" data-id="10460064" data-type="RADIO_AUDIO"></div>
<script>
    jQuery(element).on('click', function() {
        bobPlayer.startPlaying({
            channel: '6',
            live: false,
            beginDate: '2026-11-24 17:30:00',
            endDate: '2026-11-24 18:00:00',
            type: BobapPlayebleTypes.RADIO_AUDIO,
            id: '10460064',
            showNext: true,
            showPrevious: true
        });
    });
</script>
<script>
    var bobapSetup = {
    "DOM": {"id": {"play": "#bobap_play"}},
    "channels": {
        "6": {"is_back_play_enabled": true, "shortName": "mr1", "name": "Kossuth"},
        "9": {"is_back_play_enabled": true, "shortName": "mr7", "name": "Dank\\u00f3"}
    }
};
</script></body></html>'''


class TestMediaKlikk(unittest.TestCase):
    def _extract(self, page):
        ie = MediaKlikkAudioIE(FakeYDL())
        ie._download_webpage = lambda *a, **kw: page
        return ie.extract(AUDIO_URL)

    def test_url_matching(self):
        self.assertTrue(MediaKlikkAudioIE.suitable(AUDIO_URL))
        self.assertFalse(MediaKlikkIE.suitable(AUDIO_URL))
        self.assertTrue(MediaKlikkIE.suitable(VIDEO_URL))
        self.assertFalse(MediaKlikkAudioIE.suitable(VIDEO_URL))
        self.assertEqual(
            MediaKlikkAudioIE._match_valid_url(
                'https://mediaklikk.hu/audio/bartok-radio/2026/11/11/06-05/klasszikus-zene/muzsikalo-reggel/',
            ).group('id'), 'muzsikalo-reggel')
        for url in (
            'https://mediaklikk.hu/audio/',
            'https://mediaklikk.hu/audio/kossuth-radio/',
            'https://mediaklikk.hu/audio/kossuth-radio/2026/11/24/esti-kronika/',
            'https://mediaklikk.hu/podcast/2026/11/24/17-30/esti-kronika/',
        ):
            self.assertFalse(MediaKlikkAudioIE.suitable(url), url)

    def test_audio_extraction(self):
        info = self._extract(AUDIO_PAGE)
        self.assertEqual(info['id'], '10460064')
        self.assertEqual(info['display_id'], 'esti-kronika')
        self.assertEqual(info['title'], 'Esti krónika')
        self.assertEqual(info['channel'], 'Kossuth')
        self.assertEqual(info['channel_id'], 'mr1')
        self.assertEqual(info['release_date'], '20261124')
        self.assertEqual(info['duration'], 1800)
        self.assertEqual(len(info['formats']), 1)
        self.assertEqual(
            info['formats'][0]['url'],
            'https://hangtar-cdn.connectmedia.hu/20261124173000/20261124180000/mr1.mp3')
        self.assertEqual(info['formats'][0]['vcodec'], 'none')

    def test_missing_player_data(self):
        with self.assertRaisesRegex(ExtractorError, 'Unable to extract player data'):
            self._extract('<html><h2 class="aod_title">x</h2></html>')

    def test_malformed_player_data(self):
        page = AUDIO_PAGE.replace('2026-11-24 17:30:00', 'garbage')
        with self.assertRaisesRegex(ExtractorError, 'Unable to extract player data'):
            self._extract(page)

    def test_unknown_channel(self):
        with self.assertRaisesRegex(ExtractorError, 'Unable to find stream name'):
            self._extract(AUDIO_PAGE.replace("channel: '6'", "channel: '99'"))


if __name__ == '__main__':
    unittest.main()
