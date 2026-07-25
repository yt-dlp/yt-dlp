#!/usr/bin/env python3

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.extractor.niconicochannelplus import NiconicoChannelPlusBaseIE


class NiconicoChannelPlusBaseIETest(NiconicoChannelPlusBaseIE):
    def _download_json(self, url, video_id, **kwargs):
        self.request = {'url': url, 'video_id': video_id, **kwargs}
        return {'data': {'content_providers': {'fanclub_site': {'id': 815}}}}


class TestNiconicoChannelPlusBaseIE(unittest.TestCase):
    def test_find_fanclub_site_id_uses_channel_domain_api(self):
        ie = NiconicoChannelPlusBaseIETest()

        self.assertEqual(ie._find_fanclub_site_id('okazuradio'), 815)
        self.assertEqual(ie.request, {
            'url': 'https://api.nicochannel.jp/fc/content_providers/channel_domain',
            'video_id': 'channels/okazuradio',
            'headers': {
                'fc_site_id': '1',
                'fc_use_device': 'null',
            },
            'query': {'current_site_domain': 'https://nicochannel.jp/okazuradio'},
            'note': 'Fetching channel info',
            'errnote': 'Unable to fetch channel info',
        })
        self.assertEqual(ie._fanclub_site_id, 815)
