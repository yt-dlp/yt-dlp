from .common import InfoExtractor

from ..utils import (
    clean_html,
    format_field,
    unified_timestamp,
    urlencode_postdata,
    strip_or_none,
)


class ParlerIE(InfoExtractor):
    IE_DESC = "Extract videos from posts on parler.com"
    _UUID_RE = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    _VALID_URL = r'https://parler\.com/feed/(?P<id>%s)' % (_UUID_RE,)
    _TESTS = [
        {
            'url': 'https://parler.com/feed/df79fdba-07cc-48fe-b085-3293897520d7',
            'md5': '16e0f447bf186bb3cf64de5bbbf4d22d',
            'info_dict': {
                'id': 'df79fdba-07cc-48fe-b085-3293897520d7',
                'ext': 'mp4',
                'title': 'Parler video #df79fdba-07cc-48fe-b085-3293897520d7',
                'description': 'md5:6f220bde2df4a97cbb89ac11f1fd8197',
                'timestamp': 1659744000,
                'upload_date': '20220806',
                'uploader': 'Tulsi Gabbard',
                'uploader_id': 'TulsiGabbard',
                'uploader_url': 'https://parler.com/TulsiGabbard',
            },
        },
        {
            'url': 'https://parler.com/feed/a7406eb4-91e5-4793-b5e3-ade57a24e287',
            'md5': '11687e2f5bb353682cee338d181422ed',
            'info_dict': {
                'id': 'a7406eb4-91e5-4793-b5e3-ade57a24e287',
                'ext': 'mp4',
                'title': 'Parler video #a7406eb4-91e5-4793-b5e3-ade57a24e287',
                'description': 'This man should run for office',
                'timestamp': 1659657600,
                'upload_date': '20220805',
                'uploader': 'Benny Johnson',
                'uploader_id': 'BennyJohnson',
                'uploader_url': 'https://parler.com/BennyJohnson',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            'https://parler.com/open-api/ParleyDetailEndpoint.php', video_id,
            data=urlencode_postdata({'uuid': video_id}))['data'][0]['primary']
        return {
            'id': video_id,
            'url': data['video_data']['videoSrc'],
            'title': "",
            'description': strip_or_none(clean_html(data.get('full_body'))) or None,
            'timestamp': unified_timestamp(data.get('date_created')),
            'uploader': strip_or_none(data.get('name')),
            'uploader_id': strip_or_none(data.get('username')),
            'uploader_url': format_field(strip_or_none(data.get('username')), None, 'https://parler.com/%s'),
        }
