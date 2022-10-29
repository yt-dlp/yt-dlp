from .common import InfoExtractor
from ..utils import (
    url_or_none,
    traverse_obj
)


class DeuxMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?2m\.ma/[^/]+/replay/single/(?P<id>(?:[A-Za-z0-9_.]{1,24})+)'

    _TESTS = [{
        'url': 'https://2m.ma/fr/replay/single/6351d439b15e1a613b3debe8',
        'info_dict': {
            'id': '6351d439b15e1a613b3debe8',
            'ext': 'mp4',
            'title': 'Grand Angle : Jeudi 20 Octobre 2022',
            'thumbnail': 'https://2msoread-ww.amagi.tv/mediasfiles/videos/images/2022/10/21/16663630861663508ea560dc8fbf20c43b3e330ff4.png'
        }
    }, {
        'url': 'https://2m.ma/fr/replay/single/635c0aeab4eec832622356da',
        'info_dict': {
            'id': '635c0aeab4eec832622356da',
            'ext': 'mp4',
            'title': 'Journal  Amazigh : Vendredi 28 Octobre 2022',
            'thumbnail': 'https://2msoread-ww.amagi.tv/mediasfiles/videos/images/2022/10/28/16669764903.png'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._download_json(
            'https://2m.ma/api/watchDetail/%s' % (video_id),
            video_id, "Downloading media JSON") or {}
        video = traverse_obj(info, ('response', 'News')) 
        title = video.get('titre')
        thumbnail = url_or_none(video.get('image'))
        return {
            'id': video_id,
            'title': title,
            'url': video.get('url'),
            'description': video.get('description'),
            'thumbnail': thumbnail
        }


class DeuxMNewsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?2m\.ma/[^/]+/news/(?P<id>(?:.)+)'

    _TESTS = [{
        'url': 'https://2m.ma/fr/news/Sahara-la-r%C3%A9solution-2654-de-l-ONU-une-confirmation-de-l-appui-%C3%A0-l-initiative-d-autonomie-Vid%C3%A9o--20221028',
        'info_dict': {
            'id': '635c4aad346a31673b1aaec3',
            'ext': 'mp4',
            'title': 'Sahara : la r\u00e9solution 2654 de l\u0027ONU, une confirmation de l\u0027appui \u00e0 l\u0027initiative d\u0027autonomie (Vid\u00e9o)',
            'description': 'md5:a240fb360871e6ffd37e1fadd813e42c',
            'thumbnail': 'https://2msoread-ww.amagi.tv/mediasfiles/videos/images/2022/10/28/16669845857-1.png'
        }
    }, {
        'url': 'https://2m.ma/fr/news/La-3%C3%A8me-conf%C3%A9rence-des-MD-Talks-Des-Ambassadeurs-et-des-Consuls-louent-le-potentiel-%C3%A9nerg%C3%A9tique-de-la-r%C3%A9gion-de-Guelmim-Oued-Noun--20221022',
        'info_dict': {
            'id': '635405760ed0533c940e7e82',
            'ext': 'mp4',
            'title': 'MD Talks: Des diplomates louent le potentiel \u00e9nerg\u00e9tique de la r\u00e9gion de Guelmim-Oued Noun ',
            'thumbnail': 'https://2msoread-ww.amagi.tv/mediasfiles/videos/images/2022/10/22/16664504981-Reportage---MD-TALKS.png'
        }
    }]

    def _real_extract(self, url):
        lang = self._search_regex(r'https?://(?:www\.)?2m\.ma/(?P<lang>(?:[a-z])+)/.*', url, 'lang')
        news_id = self._match_id(url)
        info = self._download_json(
            'https://2m.ma/api/articlesByUrl?lang=%s&url=/news/%s' % (lang, news_id),
            news_id, "Downloading media JSON") or {}
        article = traverse_obj(info, ('response', 'article'))[0]
        title = article.get('title')
        thumbnail = url_or_none(article.get('cover'))
        return {
            'id': article.get('id'),
            'title': title,
            'url': article.get('image')[0],
            'description': article.get('content'),
            'thumbnail': thumbnail
        }
