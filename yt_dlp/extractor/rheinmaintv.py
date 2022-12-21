from ..utils import extract_attributes, float_or_none, int_or_none, parse_iso8601
from .common import InfoExtractor


class RheinMainTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rheinmaintv\.de/sendungen/(?:[a-z-]+/)*(?P<display_id>[a-z-]+)/vom-(?P<date>[0-9]{2}\.[0-9]{2}\.[0-9]{4})(?:/(?P<serial_number>[0-9]+))?'
    _TESTS = [{
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften/vom-14.11.2022/',
        # 'md5': ...,  # left out because checksum is changing
        'info_dict': {
            'id': 'vom 14.11.2022',
            'ext': 'mp4',
            'title': 'Formationsgemeinschaft Rhein-Main bei den Deutschen Meisterschaften',
            'alt_title': 'Formationsgemeinschaft Rhein-Main bei den Deutschen Meisterschaften',
            'description': 'Die Lateinformation wollte bei den Deutschen Meisterschaften in die Zwischenrunde. Leider schaffte es das Team nicht.',
            'display_id': 'formationsgemeinschaft-rhein-main-bei-den-deutschen-meisterschaften',
            'formats': [{
                'format_id': 'aac_UND_2_129-128',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'ext': 'mp4',
                'width': None,
                'height': None,
                'tbr': 128,
                'asr': 48000,
                'vcodec': 'none',
                'acodec': 'AACL',
                'protocol': 'ism',
                'fragments': 'count:172',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'audio',
                    'duration': 3448320000,
                    'timescale': 10000000,
                    'width': 0,
                    'height': 0,
                    'fourcc': 'AACL',
                    'language': 'und',
                    'codec_private_data': '1190',
                    'sampling_rate': 48000,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '401',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'ext': 'mp4',
                'width': 320,
                'height': 180,
                'tbr': 401,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:173',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3448320000,
                    'timescale': 10000000,
                    'width': 320,
                    'height': 180,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764000DACD941419F9F011000000300100000030320F14299600000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '653',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'ext': 'mp4',
                'width': 640,
                'height': 360,
                'tbr': 653,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:173',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3448320000,
                    'timescale': 10000000,
                    'width': 640,
                    'height': 360,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001EACD940A02FF97011000003000100000300320F162D960000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '1005',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'ext': 'mp4',
                'width': 640,
                'height': 360,
                'tbr': 1005,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:173',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3448320000,
                    'timescale': 10000000,
                    'width': 640,
                    'height': 360,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001EACD940A02FF97011000003000100000300320F162D960000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '1505',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'ext': 'mp4',
                'width': 960,
                'height': 540,
                'tbr': 1505,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:173',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3448320000,
                    'timescale': 10000000,
                    'width': 960,
                    'height': 540,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001FACD940F0117EF011000003000100000300320F1831960000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '2260',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'ext': 'mp4',
                'width': 960,
                'height': 540,
                'tbr': 2260,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:173',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3448320000,
                    'timescale': 10000000,
                    'width': 960,
                    'height': 540,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001FACD940F0117EF011000003000100000300320F1831960000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '3415',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'ext': 'mp4',
                'width': 1280,
                'height': 720,
                'tbr': 3415,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:173',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3448320000,
                    'timescale': 10000000,
                    'width': 1280,
                    'height': 720,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001FACD9405005BB011000000300100000030320F18319600000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '4706',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'ext': 'mp4',
                'width': 1920,
                'height': 1080,
                'tbr': 4706,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:173',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3448320000,
                    'timescale': 10000000,
                    'width': 1920,
                    'height': 1080,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '0000000167640028ACD940780227E5C044000003000400000300C83C60C6580000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '6021',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/30dd92a2-20ad-4a02-97cc-c33edf83fe25/FGRheinMainDM2022.ism/manifest',
                'ext': 'mp4',
                'width': 1920,
                'height': 1080,
                'tbr': 6021,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:173',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3448320000,
                    'timescale': 10000000,
                    'width': 1920,
                    'height': 1080,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '0000000167640028ACD940780227E5C044000003000400000300C83C60C6580000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }],
            'subtitles': {},
            'thumbnail': 'https://rmtvmedia0.blob.core.windows.net/b43ca3fa-39b4-4129-9512-116c342b9a05/04_Latein.jpg?sv=2016-05-31&sr=c&sig=I6TEvoc8M2fzN6PwvIuPZ1VxxL06GnvxrjMTo7C3ys0%3D&st=2022-11-14T14%3A30%3A14Z&se=3022-11-15T14%3A30%3A14Z&sp=r',
            'timestamp': 1668526214,
            'duration': 345.0,
            'view_count': int,
            'upload_date': '20221115'
        }
    }, {
        'url': 'https://www.rheinmaintv.de/sendungen/beitrag-video/casino-mainz-bei-den-deutschen-meisterschaften/vom-14.11.2022/',
        # 'md5': ...,  # left out because checksum is changing
        'info_dict': {
            'id': 'vom 14.11.2022',
            'ext': 'mp4',
            'title': 'Casino Mainz bei den Deutschen Meisterschaften',
            'alt_title': 'Casino Mainz bei den Deutschen Meisterschaften',
            'description': 'Die Standardformation aus Mainz hoffte auch auf den Sprung in die Zwischenrunde, doch auch für sie war Schluss nach der Vorrunde.',
            'display_id': 'casino-mainz-bei-den-deutschen-meisterschaften',
            'formats': [{
                'format_id': 'aac_UND_2_129-128',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'ext': 'mp4',
                'width': None,
                'height': None,
                'tbr': 128,
                'asr': 48000,
                'vcodec': 'none',
                'acodec': 'AACL',
                'protocol': 'ism',
                'fragments': 'count:174',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'audio',
                    'duration': 3475200000,
                    'timescale': 10000000,
                    'width': 0,
                    'height': 0,
                    'fourcc': 'AACL',
                    'language': 'und',
                    'codec_private_data': '1190',
                    'sampling_rate': 48000,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '400',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'ext': 'mp4',
                'width': 320,
                'height': 180,
                'tbr': 400,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:174',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3475200000,
                    'timescale': 10000000,
                    'width': 320,
                    'height': 180,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764000DACD941419F9F011000000300100000030320F14299600000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '650',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'ext': 'mp4',
                'width': 640,
                'height': 360,
                'tbr': 650,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:174',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3475200000,
                    'timescale': 10000000,
                    'width': 640,
                    'height': 360,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001EACD940A02FF97011000003000100000300320F162D960000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '1000',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'ext': 'mp4',
                'width': 640,
                'height': 360,
                'tbr': 1000,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:174',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3475200000,
                    'timescale': 10000000,
                    'width': 640,
                    'height': 360,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001EACD940A02FF97011000003000100000300320F162D960000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '1498',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'ext': 'mp4',
                'width': 960,
                'height': 540,
                'tbr': 1498,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:174',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3475200000,
                    'timescale': 10000000,
                    'width': 960,
                    'height': 540,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001FACD940F0117EF011000003000100000300320F1831960000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '2249',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'ext': 'mp4',
                'width': 960,
                'height': 540,
                'tbr': 2249, 'asr': None, 'vcodec': 'H264', 'acodec': 'none', 'protocol': 'ism', 'fragments': 'count:174',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3475200000,
                    'timescale': 10000000,
                    'width': 960,
                    'height': 540,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001FACD940F0117EF011000003000100000300320F1831960000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '3398',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'ext': 'mp4',
                'width': 1280,
                'height': 720,
                'tbr': 3398,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:174',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3475200000,
                    'timescale': 10000000,
                    'width': 1280,
                    'height': 720,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '000000016764001FACD9405005BB011000000300100000030320F18319600000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '4689',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'ext': 'mp4',
                'width': 1920,
                'height': 1080,
                'tbr': 4689,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:174',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3475200000,
                    'timescale': 10000000,
                    'width': 1920,
                    'height': 1080,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '0000000167640028ACD940780227E5C044000003000400000300C83C60C6580000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }, {
                'format_id': '5995',
                'url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'manifest_url': 'https://rmtvmedia.streaming.mediaservices.windows.net/ee75c842-1751-44bc-bc16-bd9dcefc4303/CasinoMainz.ism/manifest',
                'ext': 'mp4',
                'width': 1920,
                'height': 1080,
                'tbr': 5995,
                'asr': None,
                'vcodec': 'H264',
                'acodec': 'none',
                'protocol': 'ism',
                'fragments': 'count:174',
                'has_drm': False,
                '_download_params': {
                    'stream_type': 'video',
                    'duration': 3475200000,
                    'timescale': 10000000,
                    'width': 1920,
                    'height': 1080,
                    'fourcc': 'H264',
                    'language': 'und',
                    'codec_private_data': '0000000167640028ACD940780227E5C044000003000400000300C83C60C6580000000168EBECB22C',
                    'sampling_rate': None,
                    'channels': 2,
                    'bits_per_sample': 16,
                    'nal_unit_length_field': 4
                }
            }],
            'subtitles': {},
            'thumbnail': 'https://rmtvmedia0.blob.core.windows.net/e1cf7655-91b9-4b7e-b19f-a79852c7b41f/06_Standard.jpg?sv=2016-05-31&sr=c&sig=jQPJSdxCxJMX8yUZkFUPNrv1qISb0pCouK9MzAMSOMc%3D&st=2022-11-14T14%3A50%3A02Z&se=3022-11-15T14%3A50%3A02Z&sp=r',
            'timestamp': 1668527402,
            'duration': 348.0,
            'view_count': int,
            'upload_date': '20221115'
        }
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('display_id')
        video_id = 'vom %s' % mobj.group('date')
        if mobj.group('serial_number'):
            video_id += ' (%s)' % mobj.group('serial_number')
        webpage = self._download_webpage(url, video_id)

        headline = self._html_search_regex(r'<h1><span class="title">([^<]*)</span>', webpage, 'headline')

        source, img = self._search_regex(r'(?s)(?P<source><source[^>]*>)(?P<img><img[^>]*>)', webpage, 'video', group=('source', 'img'))
        source = extract_attributes(source)
        img = extract_attributes(img)

        # json = self._search_json_ld(webpage, video_id)  # uncomment to extract the useless 'contentUrl' (as 'url') instead of the essential 'embedUrl'
        #                                                 # then use get(json, 'title') instead of get(json, 'name')
        json = self._parse_json(self._search_regex(r'(?s)<script type="application/ld\+json">([^<]*)</script>', webpage, 'json'), video_id)
        # json = None  # uncomment to go without ld+json altogether

        def get(dictionary, *keys):  # return ..utils.traverse_obj(dictionary, keys)
            for k in keys:
                if dictionary is None:
                    return None
                dictionary = dictionary.get(k)
            return dictionary

        formats, subtitles = self._extract_ism_formats_and_subtitles(source['src'] or get(json, 'embedUrl'), video_id)  # attribute 'src' is mandatory

        def removeprefix(string, prefix):
            return string[len(prefix):] if string.startswith(prefix) else None

        def extract_format(internet_media_type, media):  # subtype of media (aka type)
            return removeprefix(internet_media_type, media + '/') if internet_media_type is not None else None

        extension = extract_format(source.get('type'), 'video')  # use video format as filename extension (!?)
        if extension:
            for f in formats:
                f['ext'] = extension

        return {
            'id': video_id,
            'title': headline or img.get('title') or get(json, 'name') or self._og_search_title(webpage) or self._html_extract_title(webpage).removesuffix(' -'),
            'alt_title': img['alt'],  # attribute 'alt' is mandatory
            'description': get(json, 'description') or self._og_search_description(webpage),
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': img['src'] or get(json, 'thumbnailUrl'),  # attribute 'src' is mandatory
            'timestamp': parse_iso8601(get(json, 'uploadDate')),
            'duration': float_or_none(get(json, 'duration')),
            'view_count': int_or_none(get(json, 'interactionStatistic', 'userInteractionCount'))
        }
