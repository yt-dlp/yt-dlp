from .common import InfoExtractor
from ..utils import url_or_none


class DeuxMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?2m\.ma/[^/]+/replay/single/(?P<id>([\w.]{1,24})+)'

    _TESTS = [{
        'url': 'https://2m.ma/fr/replay/single/6351d439b15e1a613b3debe8',
        'md5': '7ab69a170493c7b7c3febe2ad965c9fd',
        'info_dict': {
            'id': '6351d439b15e1a613b3debe8',
            'ext': 'mp4',
            'title': 'Grand Angle : Jeudi 20 Octobre 2022',
            'thumbnail': 'https://2msoread-ww.amagi.tv/mediasfiles/videos/images/2022/10/21/16663630861663508ea560dc8fbf20c43b3e330ff4.png'
        }
    }, {
        'url': 'https://2m.ma/fr/replay/single/635c0aeab4eec832622356da',
        'md5': 'ad6af2f5e4d5b2ad2194a84b6e890b4c',
        'info_dict': {
            'id': '635c0aeab4eec832622356da',
            'ext': 'mp4',
            'title': 'Journal  Amazigh : Vendredi 28 Octobre 2022',
            'thumbnail': 'https://2msoread-ww.amagi.tv/mediasfiles/videos/images/2022/10/28/16669764903.png'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video = self._download_json(
            f'https://2m.ma/api/watchDetail/{video_id}', video_id)['response']['News']
        return {
            'id': video_id,
            'title': video.get('titre'),
            'url': video['url'],
            'description': video.get('description'),
            'thumbnail': url_or_none(video.get('image')),
        }


class DeuxMNewsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?2m\.ma/(?P<lang>\w+)/news/(?P<id>[^/#?]+)'

    _TESTS = [{
        'url': 'https://2m.ma/fr/news/Kan-Ya-Mkan-d%C3%A9poussi%C3%A8re-l-histoire-du-phare-du-Cap-Beddouza-20221028',
        'md5': 'f434e2552b1bd1004fc04737b59c03a9',
        'info_dict': {
            'id': '635c5d1233b83834e35b282e',
            'ext': 'mp4',
            'title': 'Kan Ya Mkan d\u00e9poussi\u00e8re l\u2019histoire du phare du Cap Beddouza',
            'description': 'md5:99dcf29b82f1d7f2a4acafed1d487527',
            'thumbnail': 'https://2msoread-ww.amagi.tv/mediasfiles/videos/images/2022/10/27/1666869608ba-kane-ya-mkane-27-10-2022.png'
        }
    }, {
        'url': 'https://2m.ma/fr/news/Interview-Casablanca-hors-des-sentiers-battus-avec-Abderrahim-KASSOU-Replay--20221017',
        'md5': '7aca29f02230945ef635eb8290283c0c',
        'info_dict': {
            'id': '634d9e108b70d40bc51a844b',
            'ext': 'mp4',
            'title': 'Interview: Casablanca hors des sentiers battus avec Abderrahim KASSOU (Replay) ',
            'description': 'md5:3b8e78111de9fcc6ef7f7dd6cff2430c',
            'thumbnail': 'https://2msoread-ww.amagi.tv/mediasfiles/videos/images/2022/10/17/1666031205e8b5613cf7fd24cc10a116844b23bfd4.png'
        }
    }]

    def _real_extract(self, url):
        article_name, lang = self._match_valid_url(url).group('id', 'lang')
        video = self._download_json(
            f'https://2m.ma/api/articlesByUrl?lang={lang}&url=/news/{article_name}', article_name)['response']['article'][0]
        return {
            'id': video['id'],
            'title': video.get('title'),
            'url': video['image'][0],
            'description': video.get('content'),
            'thumbnail': url_or_none(video.get('cover')),
        }
