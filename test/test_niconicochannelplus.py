#!/usr/bin/env python3

import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.cookies import (
    extract_firefox_nicochannel_auth0_tokens,
    update_firefox_nicochannel_auth0_tokens,
)
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

    def test_extracts_auth0_access_token_from_firefox_local_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = os.path.join(tmpdir, 'data.sqlite')
            with sqlite3.connect(database_path) as connection:
                connection.execute(
                    'CREATE TABLE data (key TEXT, compression_type INTEGER, value BLOB)')
                connection.execute(
                    'INSERT INTO data VALUES (?, ?, ?)', (
                        'persist:auth', 0,
                        b'{"totalUserInformation":"{\\"root\\":{\\"userInformation\\":{\\"accessToken\\":\\"test-token\\"}}}"}'))
                connection.execute(
                    'INSERT INTO data VALUES (?, ?, ?)', (
                        '@@auth0spajs@@::client-id::api.nicochannel.jp::scope',
                        0, b'{"body":{"refresh_token":"refresh-token"}}'))
            with patch('yt_dlp.cookies._firefox_local_storage_dbs', return_value=[database_path]):
                self.assertEqual(
                    extract_firefox_nicochannel_auth0_tokens(None),
                    ('test-token', 'refresh-token', 'client-id', database_path))
                self.assertTrue(update_firefox_nicochannel_auth0_tokens(
                    database_path, 'new-token', 'new-refresh-token'))
                self.assertEqual(
                    extract_firefox_nicochannel_auth0_tokens(None),
                    ('new-token', 'new-refresh-token', 'client-id', database_path))

    def test_refreshes_auth0_access_token(self):
        ie = NiconicoChannelPlusBaseIE()
        ie._auth0_tokens = ('old-token', 'refresh-token', 'client-id', 'data.sqlite')
        with (
            patch.object(ie, '_download_json', return_value={
                'access_token': 'new-token', 'refresh_token': 'new-refresh-token'}) as download_json,
            patch('yt_dlp.extractor.niconicochannelplus.can_update_firefox_nicochannel_auth0_tokens', return_value=True),
            patch('yt_dlp.extractor.niconicochannelplus.update_firefox_nicochannel_auth0_tokens', return_value=True),
        ):
            self.assertTrue(ie._refresh_auth0_access_token())
        self.assertEqual(ie._auth0_tokens, ('new-token', 'new-refresh-token', 'client-id', 'data.sqlite'))
        download_json.assert_called_once_with(
            'https://auth.nicochannel.jp/oauth/token', video_id='auth',
            data=b'client_id=client-id&grant_type=refresh_token&refresh_token=refresh-token',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            note='Refreshing Niconico Channel Plus login',
            errnote='Unable to refresh Niconico Channel Plus login',
        )
