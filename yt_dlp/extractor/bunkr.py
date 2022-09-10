import json

from ..utils import get_element_by_id, traverse_obj
from .common import InfoExtractor


class BunkrIE(InfoExtractor):
    _TYPE = 'url'
    _VALID_URL = r'^https://(stream\.bunkr\.is/v|cdn\d?\.bunkr\.is)/(?P<id>\S+)$'
    _TESTS = [
        {
            'url': 'https://stream.bunkr.is/v/bigbuckbunny-b4VHMTTI.mp4',
            'md5': 'c0c859bcf2a1ebfcab2f968679738721',
            'info_dict': {
                'id': 'bigbuckbunny-b4VHMTTI',
                'title': 'bigbuckbunny-b4VHMTTI',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://cdn4.bunkr.is/bigbuckbunny-b4VHMTTI.mp4',
            'md5': 'c0c859bcf2a1ebfcab2f968679738721',
            'info_dict': {
                'id': 'bigbuckbunny-b4VHMTTI',
                'title': 'bigbuckbunny-b4VHMTTI',
                'ext': 'mp4',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data = traverse_obj(json.loads(get_element_by_id('__NEXT_DATA__', webpage)), ('props', 'pageProps', 'file'))
        # Example data:
        # {
        #     "name": "bigbuckbunny-b4VHMTTI.mp4",
        #     "size": "4233370",
        #     "mediafiles": "https://media-files4.bunkr.is"
        # }

        id = '.'.join(data.get('name').split('.')[:-1])

        return {
            'id': id,
            'title': id,
            'formats': [{
                'url': data.get('mediafiles') + '/' + data.get('name'),
                'filesize': int(data.get('size')),
            }],
        }


class BunkrAlbumIE(InfoExtractor):
    _TYPE = 'url'
    _VALID_URL = r'^https://bunkr\.is/a/(?P<id>\S+)$'
    _TESTS = [
        {
            'url': 'https://bunkr.is/a/hNJhvMle',
            'info_dict': {
                'id': 'hNJhvMle',
                'title': 'big buck playlist',
            },
            'playlist': [
                {
                    'info_dict': {
                        'id': 'bigbuck_004-dUyla0ux',
                        'title': 'bigbuck_004-dUyla0ux',
                        'ext': 'mp4',
                        'timestamp': 1661345586,
                        'upload_date': '20220824',
                    },
                },
                {
                    'info_dict': {
                        'id': 'bigbuck_003-lqaPgktY',
                        'title': 'bigbuck_003-lqaPgktY',
                        'ext': 'mp4',
                        'timestamp': 1661345636,
                        'upload_date': '20220824',
                    },
                },
                {
                    'info_dict': {
                        'id': 'bigbuck_001-mazOX2V2',
                        'title': 'bigbuck_001-mazOX2V2',
                        'ext': 'mp4',
                        'timestamp': 1661345685,
                        'upload_date': '20220824',
                    },
                },
                {
                    'info_dict': {
                        'id': 'bigbuck_002-eVZJ4jY9',
                        'title': 'bigbuck_002-eVZJ4jY9',
                        'ext': 'mp4',
                        'timestamp': 1661345774,
                        'upload_date': '20220824',
                    },
                },
            ],
        },
    ]

    def _extract_entries(self, data):
        for f in data.get('files'):
            id = '.'.join(f.get('name').split('.')[:-1])

            yield {
                'id': id,
                'title': id,
                'formats': [{
                    'url': f.get('cdn').replace('cdn', 'media-files') + '/' + f.get('name'),
                    'filesize': int(f.get('size')),
                    'timestamp': f.get('timestamp'),
                }],
            }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data = traverse_obj(json.loads(get_element_by_id('__NEXT_DATA__', webpage)), ('props', 'pageProps', 'album'))
        # Example data:
        # {
        #     "id": 55378,
        #     "name": "big buck playlist",
        #     "identifier": "hNJhvMle",
        #     "enabled": 1,
        #     "public": 1,
        #     "description": "",
        #     "notFound": false,
        #     "files": [
        #         {
        #             "name": "bigbuck_004-dUyla0ux.mp4",
        #             "size": "9462607",
        #             "timestamp": 1661345586,
        #             "cdn": "https://cdn4.bunkr.is",
        #             "i": "https://i4.bunkr.is"
        #         },
        #         {
        #             "name": "bigbuck_003-lqaPgktY.mp4",
        #             "size": "9800947",
        #             "timestamp": 1661345636,
        #             "cdn": "https://cdn4.bunkr.is",
        #             "i": "https://i4.bunkr.is"
        #         },
        #         {
        #             "name": "bigbuck_001-mazOX2V2.mp4",
        #             "size": "2917670",
        #             "timestamp": 1661345685,
        #             "cdn": "https://cdn4.bunkr.is",
        #             "i": "https://i4.bunkr.is"
        #         },
        #         {
        #             "name": "bigbuck_002-eVZJ4jY9.mp4",
        #             "size": "10508190",
        #             "timestamp": 1661345774,
        #             "cdn": "https://cdn4.bunkr.is",
        #             "i": "https://i4.bunkr.is"
        #         }
        #     ]
        # }

        playlist_id = data.get('identifier')
        return self.playlist_result(self._extract_entries(data), playlist_id, data.get('name') or playlist_id)
