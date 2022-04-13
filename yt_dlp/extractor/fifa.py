from .common import InfoExtractor

from ..utils import (
    int_or_none,
    traverse_obj,
    unified_timestamp,
)


class FifaIE(InfoExtractor):
    _VALID_URL = r'https?://www.fifa.com/fifaplus/(?P<locale>\w{2})/watch/(?P<id>\w+)/?'
    _TESTS = [{
        'url': 'https://www.fifa.com/fifaplus/en/watch/7on10qPcnyLajDDU3ntg6y',
        'info_dict': {
            'id': '7on10qPcnyLajDDU3ntg6y',
            'title': 'Italy v France | Final | 2006 FIFA World Cup Germany™ | Full Match Replay',
            'description': 'md5:f4520d0ee80529c8ba4134a7d692ff8b',
            'ext': 'mp4',
            'categories': ['FIFA Tournaments', 'Replay'],
            'thumbnail': 'https://digitalhub.fifa.com/transform/fa6f0b3e-a2e9-4cf7-9f32-53c57bcb7360/2006_Final_ITA_FRA',
            'duration': 8164,
        },
        'expected_warnings': ['The stream has AES-128 encryption and neither ffmpeg nor pycryptodomex are available; Decryption will be performed natively, but will be extremely slow'],
    }, {
        'url': 'https://www.fifa.com/fifaplus/pt/watch/1cg5r5Qt6Qt12ilkDgb1sV',
        'info_dict': {
            'id': '1cg5r5Qt6Qt12ilkDgb1sV',
            'title': 'Brasil x Alemanha | Semifinais | Copa do Mundo FIFA Brasil 2014 | Compacto',
            'description': 'md5:ba4ffcc084802b062beffc3b4c4b19d6',
            'ext': 'mp4',
            'categories': ['FIFA Tournaments', 'Highlights'],
            'thumbnail': 'https://digitalhub.fifa.com/transform/d8fe6f61-276d-4a73-a7fe-6878a35fd082/FIFAPLS_100EXTHL_2014BRAvGER_TMB',
            'duration': 901,
            'release_timestamp': 1404777600,
            'release_date': '20140708',
        },
        'expected_warnings': ['The stream has AES-128 encryption and neither ffmpeg nor pycryptodomex are available; Decryption will be performed natively, but will be extremely slow'],
    }, {
        'url': 'https://www.fifa.com/fifaplus/fr/watch/3C6gQH9C2DLwzNx7BMRQdp',
        'info_dict': {
            'id': '3C6gQH9C2DLwzNx7BMRQdp',
            'title': 'Le but de Josimar contre le Irlande du Nord | Buts classiques',
            'description': 'md5:16f9f789f09960bfe7220fe67af31f34',
            'ext': 'mp4',
            'categories': ['FIFA Tournaments', 'Goal'],
            'duration': 28,
            'thumbnail': 'https://digitalhub.fifa.com/transform/f9301391-f8d9-48b5-823e-c093ac5e3e11/CG_MEN_1986_JOSIMAR',
        },
        'expected_warnings': ['The stream has AES-128 encryption and neither ffmpeg nor pycryptodomex are available; Decryption will be performed natively, but will be extremely slow'],
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        locale = mobj.group('locale')
        webpage = self._download_webpage(url, video_id)

        preconnect_link = self._search_regex(r'<link[^>]+?rel\s*=\s*"preconnect"[^>]+href\s*=\s*"([^"]+)"', webpage, 'Preconnect Link')

        json_data = self._download_json(f'{preconnect_link}/video/GetVideoPlayerData/{video_id}',
                                        video_id, 'Downloading Video Player Data', query={'includeIdents': True, 'locale': locale})

        video_details = self._download_json(f'{preconnect_link}/sections/videoDetails/{video_id}', video_id, 'Downloading Video Details', fatal=False)

        preplay_parameters = self._download_json(
            f'{preconnect_link}/video/GetVerizonPreplayParameters', video_id, 'Downloading Preplay Parameters', query={
                'entryId': video_id,
                'assetId': json_data.get('verizonAssetId'),
                'useExternalId': False,
                'requiresToken': json_data.get('requiresToken'),
                'adConfig': 'fifaplusvideo',
                'prerollAds': True,
                'adVideoId': json_data.get('externalVerizonAssetId'),
                'preIdentId': json_data.get('preIdentId'),
                'postIdentId': json_data.get('postIdentId'),
            })

        cid = f'{json_data.get("preIdentId")},{json_data.get("verizonAssetId")},{json_data.get("postIdentId")}'
        content_data = self._download_json(
            f'https://content.uplynk.com/preplay/{cid}/multiple.json', video_id, 'Downloading Content Data', query={
                'v': preplay_parameters.get('preplayAPIVersion'),
                'tc': preplay_parameters.get('tokenCheckAlgorithmVersion'),
                'rn': preplay_parameters.get('randomNumber'),
                'exp': preplay_parameters.get('tokenExpirationDate'),
                'ct': preplay_parameters.get('contentType'),
                'cid': cid,
                'mbtracks': preplay_parameters.get('tracksAssetNumber'),
                'ad': preplay_parameters.get('adConfiguration'),
                'ad.preroll': int(preplay_parameters.get('adPreroll')),
                'ad.cmsid': preplay_parameters.get('adCMSSourceId'),
                'ad.vid': preplay_parameters.get('adSourceVideoID'),
                'sig': preplay_parameters.get('signature'),
            })

        formats = self._extract_m3u8_formats(
            content_data.get('playURL'), video_id, note='Downloading m3u8 Information')

        return {
            'id': video_id,
            'title': json_data.get('title'),
            'description': json_data.get('description'),
            'duration': int_or_none(json_data.get('duration')),
            'release_timestamp': unified_timestamp(video_details.get('dateOfRelease')),
            'categories': [video_details.get('videoCategory'), video_details.get('videoSubcategory')],
            'thumbnail': traverse_obj(video_details, ('backgroundImage', 'src')),
            'formats': formats,
        }
