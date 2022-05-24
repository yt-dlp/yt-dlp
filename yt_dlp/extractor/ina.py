from .common import InfoExtractor
from ..utils import unified_strdate


class InaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|m)\.)?ina\.fr/(?:[^/]+/)?(?:video|audio)/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.ina.fr/video/I12055569/francois-hollande-je-crois-que-c-est-clair-video.html',
        'md5': 'c5a09e5cb5604ed10709f06e7a377dda',
        'info_dict': {
            'id': 'I12055569',
            'ext': 'mp4',
            'title': 'François Hollande "Je crois que c\'est clair"',
            'description': 'md5:08201f1c86fb250611f0ba415d21255a',
            'upload_date': '20070712',
            'thumbnail': 'https://cdn-hub.ina.fr/notice/690x517/3c4/I12055569.jpeg',
        }
    }, {
        'url': 'https://www.ina.fr/video/S806544_001/don-d-organes-des-avancees-mais-d-importants-besoins-video.html',
        'only_matching': True,
    }, {
        'url': 'https://www.ina.fr/audio/P16173408',
        'only_matching': True,
    }, {
        'url': 'https://www.ina.fr/video/P16173408-video.html',
        'only_matching': True,
    }, {
        'url': 'http://m.ina.fr/video/I12055569',
        'only_matching': True,
    }, {
        'url': 'https://www.ina.fr/ina-eclaire-actu/video/cpb8205116303/les-jeux-electroniques',
        'md5': '4b8284a9a3a184fdc7e744225b8251e7',
        'info_dict': {
            'id': 'CPB8205116303',
            'ext': 'mp4',
            'title': 'Les jeux électroniques',
            'description': 'md5:e09f7683dad1cc60b74950490127d233',
            'upload_date': '19821204',
            'duration': 657,
            'thumbnail': 'https://cdn-hub.ina.fr/notice/690x517/203/CPB8205116303.jpeg',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).upper()
        webpage = self._download_webpage(url, video_id)

        api_url = self._html_search_regex(
            r'asset-details-url\s*=\s*["\'](?P<api_url>[^"\']+)',
            webpage, 'api_url').replace(video_id, f'{video_id}.json')

        api_response = self._download_json(api_url, video_id)

        return {
            'id': video_id,
            'url': api_response['resourceUrl'],
            'ext': {'video': 'mp4', 'audio': 'mp3'}.get(api_response.get('type')),
            'title': api_response.get('title'),
            'description': api_response.get('description'),
            'upload_date': unified_strdate(api_response.get('dateOfBroadcast')),
            'duration': api_response.get('duration'),
            'thumbnail': api_response.get('resourceThumbnail'),
        }
