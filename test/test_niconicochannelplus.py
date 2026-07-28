#!/usr/bin/env python3

import contextlib
import os
import sqlite3
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.cookies import extract_firefox_nicochannel_auth0_client
from yt_dlp.extractor.niconicochannelplus import NiconicoChannelPlusBaseIE, NiconicoChannelPlusIE
from yt_dlp.utils import ExtractorError


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

    def test_extracts_auth0_client_from_firefox_local_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = os.path.join(tmpdir, 'data.sqlite')
            with contextlib.closing(sqlite3.connect(database_path)) as connection:
                with connection:
                    connection.execute(
                        'CREATE TABLE data (key TEXT, compression_type INTEGER, value BLOB)')
                    connection.execute(
                        'INSERT INTO data VALUES (?, ?, ?)', (
                            '@@auth0spajs@@::client-id::api.nicochannel.jp::scope',
                            0, b''))
            with patch('yt_dlp.cookies._firefox_local_storage_dbs', return_value=[database_path]):
                self.assertEqual(
                    extract_firefox_nicochannel_auth0_client(None), ('client-id', 'scope'))

    def test_refreshes_auth0_access_token(self):
        ie = NiconicoChannelPlusBaseIE()
        ie._auth0_client = ('client-id', 'scope')
        with (
            patch('yt_dlp.extractor.niconicochannelplus.secrets.token_urlsafe', side_effect=('verifier', 'state')),
            patch.object(ie, '_download_webpage_handle', return_value=(
                '', SimpleNamespace(url='https://nicochannel.jp/login/login-redirect?code=code&state=state'))),
            patch.object(ie, '_download_json', return_value={'access_token': 'new-token'}) as download_json,
        ):
            self.assertEqual(ie._refresh_auth0_access_token(), 'new-token')
        download_json.assert_called_once_with(
            'https://auth.nicochannel.jp/oauth/token', video_id='auth',
            data=b'client_id=client-id&code=code&code_verifier=verifier&grant_type=authorization_code&redirect_uri=https%3A%2F%2Fnicochannel.jp%2Flogin%2Flogin-redirect',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            note=False,
            errnote='Unable to exchange Niconico Channel Plus login',
        )

    def test_refreshes_auth0_access_token_after_session_timeout(self):
        ie = NiconicoChannelPlusIE()
        ie._channel_id = 'channel'
        requests = []
        session_requests = 0

        def download_json(url, video_id, **kwargs):
            nonlocal session_requests
            requests.append((url, video_id, kwargs))
            if url == 'https://auth.nicochannel.jp/oauth/token':
                return {'access_token': f'token-{session_requests + 1}'}
            session_requests += 1
            if session_requests == 1:
                raise ExtractorError('session timed out', cause=SimpleNamespace(status=408))
            return {'data': {'session_id': 'session-id'}}

        def download_webpage_handle(url, video_id, **kwargs):
            return '', SimpleNamespace(
                url=f'https://nicochannel.jp/login/login-redirect?code=code&state={kwargs["query"]["state"]}')

        with (
            patch('yt_dlp.extractor.niconicochannelplus.extract_firefox_nicochannel_auth0_client', return_value=('client-id', 'scope')) as extract_client,
            patch.object(ie, 'get_param', return_value=('firefox', 'profile', None, None)),
            patch.object(ie, '_download_json', side_effect=download_json),
            patch.object(ie, '_download_webpage_handle', side_effect=download_webpage_handle),
            patch.object(ie, 'write_debug'),
        ):
            self.assertEqual(ie._get_live_status_and_session_id('content', {'type': 'vod'}), ('not_live', 'session-id'))

        extract_client.assert_called_once_with('profile')
        self.assertEqual([
            request[2]['headers']['Authorization']
            for request in requests
            if request[0] == 'https://api.nicochannel.jp/fc/video_pages/content/session_ids'
        ], ['Bearer token-1', 'Bearer token-2'])
