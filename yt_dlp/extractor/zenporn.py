import base64
import binascii

from .common import InfoExtractor
from ..utils import ExtractorError, determine_ext, unified_strdate, url_or_none
from ..utils.traversal import traverse_obj


class ZenPornIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?zenporn\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://zenporn.com/video/15627016/desi-bhabi-ki-chudai',
        'md5': '07bd576b5920714d74975c054ca28dee',
        'info_dict': {
            'id': '9563799',
            'display_id': '15627016',
            'ext': 'mp4',
            'title': 'md5:669eafd3bbc688aa29770553b738ada2',
            'description': '',
            'thumbnail': 'md5:2fc044a19bab450fef8f1931e7920a18',
            'upload_date': '20230925',
            'uploader': 'md5:9fae59847f1f58d1da8f2772016c12f3',
            'age_limit': 18,
        }
    }, {
        'url': 'https://zenporn.com/video/15570701',
        'md5': 'acba0d080d692664fcc8c4e5502b1a67',
        'info_dict': {
            'id': '2297875',
            'display_id': '15570701',
            'ext': 'mp4',
            'title': 'md5:47aebdf87644ec91e8b1a844bc832451',
            'description': '',
            'thumbnail': 'https://mstn.nv7s.com/contents/videos_screenshots/2297000/2297875/480x270/1.jpg',
            'upload_date': '20230921',
            'uploader': 'Lois Clarke',
            'age_limit': 18,
        }
    }, {
        'url': 'https://zenporn.com/video/8531117/amateur-students-having-a-fuck-fest-at-club/',
        'md5': '67411256aa9451449e4d29f3be525541',
        'info_dict': {
            'id': '12791908',
            'display_id': '8531117',
            'ext': 'mp4',
            'title': 'Amateur students having a fuck fest at club',
            'description': '',
            'thumbnail': 'https://tn.txxx.tube/contents/videos_screenshots/12791000/12791908/288x162/1.jpg',
            'upload_date': '20191005',
            'uploader': 'Jackopenass',
            'age_limit': 18,
        }
    }, {
        'url': 'https://zenporn.com/video/15872038/glad-you-came/',
        'md5': '296ccab437f5bac6099433768449d8e1',
        'info_dict': {
            'id': '111585',
            'display_id': '15872038',
            'ext': 'mp4',
            'title': 'Glad You Came',
            'description': '',
            'thumbnail': 'https://vpim.m3pd.com/contents/videos_screenshots/111000/111585/480x270/1.jpg',
            'upload_date': '20231024',
            'uploader': 'Martin Rudenko',
            'age_limit': 18,
        }
    }]

    def _gen_info_url(self, ext_domain, extr_id, lifetime=86400):
        """ This function is a reverse engineering from the website javascript """
        result = '/'.join(str(int(extr_id) // i * i) for i in (1_000_000, 1_000, 1))
        return f'https://{ext_domain}/api/json/video/{lifetime}/{result}.json'

    @staticmethod
    def _decode_video_url(encoded_url):
        """ This function is a reverse engineering from the website javascript """
        # Replace lookalike characters and standardize map
        translation = str.maketrans('АВСЕМ.,~', 'ABCEM+/=')
        try:
            return base64.b64decode(encoded_url.translate(translation), validate=True).decode()
        except (binascii.Error, ValueError):
            return None

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        ext_domain, video_id = self._search_regex(
            r'https://(?P<ext_domain>[\w.-]+\.\w{3})/embed/(?P<extr_id>\d+)/',
            webpage, 'embed info', group=('ext_domain', 'extr_id'))

        info_json = self._download_json(
            self._gen_info_url(ext_domain, video_id), video_id, fatal=False)

        video_json = self._download_json(
            f'https://{ext_domain}/api/videofile.php', video_id, query={
                'video_id': video_id,
                'lifetime': 8640000,
            }, note='Downloading video file JSON', errnote='Failed to download video file JSON')

        decoded_url = self._decode_video_url(video_json[0]['video_url'])
        if not decoded_url:
            raise ExtractorError('Unable to decode the video url')

        return {
            'id': video_id,
            'display_id': display_id,
            'ext': traverse_obj(video_json, (0, 'format', {determine_ext})),
            'url': f'https://{ext_domain}{decoded_url}',
            'age_limit': 18,
            **traverse_obj(info_json, ('video', {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('thumb', {url_or_none}),
                'upload_date': ('post_date', {unified_strdate}),
                'uploader': ('user', 'username', {str}),
            })),
        }
