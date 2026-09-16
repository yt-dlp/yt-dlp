import unittest
from unittest.mock import patch

from test.helper import FakeYDL
from yt_dlp.extractor.neteasemusic import NetEaseMusicAlbumIE, NetEaseMusicIE


class TestNetEaseMusicAlbumIE(unittest.TestCase):
    def test_extracts_album_from_api(self):
        ie = NetEaseMusicAlbumIE(FakeYDL())
        album_id = '12345'
        api_response = {
            'songs': [{'id': 67890, 'name': 'A song'}],
            'album': {
                'name': 'An album',
                'description': 'Album description',
                'picUrl': 'https://example.com/album.jpg',
                'publishTime': 1693526400000,
            },
        }

        with (
            patch.object(ie, '_query_api', return_value=api_response) as query_api,
            patch.object(ie, '_download_webpage', side_effect=AssertionError('Unexpected HTML request')),
        ):
            result = ie._real_extract(f'https://music.163.com/#/album?id={album_id}')

        query_api.assert_called_once_with(f'v1/album/{album_id}', album_id, 'Downloading album info')
        self.assertEqual(result['id'], album_id)
        self.assertEqual(result['title'], 'An album')
        self.assertEqual(result['description'], 'Album description')
        self.assertEqual(result['thumbnail'], 'https://example.com/album.jpg')
        self.assertEqual(result['upload_date'], '20230901')
        self.assertEqual(list(result['entries']), [{
            '_type': 'url',
            'ie_key': NetEaseMusicIE.ie_key(),
            'id': '67890',
            'title': 'A song',
            'url': 'http://music.163.com/#/song?id=67890',
        }])


if __name__ == '__main__':
    unittest.main()
