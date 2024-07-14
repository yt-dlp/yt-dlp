import json
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    str_or_none,
    try_get,
)


class TelecincoIE(InfoExtractor):
    IE_DESC = 'telecinco.es, cuatro.com and mediaset.es'
    _VALID_URL = r'https?://(?:www\.)?(?:telecinco\.es|cuatro\.com|mediaset\.es)/(?:[^/]+/)+(?P<id>.+?)\.html'

    _TESTS = [{
        'url': 'http://www.telecinco.es/robinfood/temporada-01/t01xp14/Bacalao-cocochas-pil-pil_0_1876350223.html',
        'info_dict': {
            'id': '1876350223',
            'title': 'Bacalao con kokotxas al pil-pil',
            'description': 'md5:716caf5601e25c3c5ab6605b1ae71529',
        },
        'playlist': [{
            'md5': '7ee56d665cfd241c0e6d80fd175068b0',
            'info_dict': {
                'id': 'JEA5ijCnF6p5W08A1rNKn7',
                'ext': 'mp4',
                'title': 'Con Martín Berasategui, hacer un bacalao al pil-pil es fácil y divertido',
                'duration': 662,
            },
        }],
    }, {
        'url': 'http://www.cuatro.com/deportes/futbol/barcelona/Leo_Messi-Champions-Roma_2_2052780128.html',
        'md5': 'c86fe0d99e3bdb46b7950d38bf6ef12a',
        'info_dict': {
            'id': 'jn24Od1zGLG4XUZcnUnZB6',
            'ext': 'mp4',
            'title': '¿Quién es este ex futbolista con el que hablan Leo Messi y Luis Suárez?',
            'description': 'md5:a62ecb5f1934fc787107d7b9a2262805',
            'duration': 79,
        },
    }, {
        'url': 'http://www.mediaset.es/12meses/campanas/doylacara/conlatratanohaytrato/Ayudame-dar-cara-trata-trato_2_1986630220.html',
        'md5': 'eddb50291df704ce23c74821b995bcac',
        'info_dict': {
            'id': 'aywerkD2Sv1vGNqq9b85Q2',
            'ext': 'mp4',
            'title': '#DOYLACARA. Con la trata no hay trato',
            'description': 'md5:2771356ff7bfad9179c5f5cd954f1477',
            'duration': 50,
        },
    }, {
        # video in opening's content
        'url': 'https://www.telecinco.es/vivalavida/fiorella-sobrina-edmundo-arrocet-entrevista_18_2907195140.html',
        'info_dict': {
            'id': '2907195140',
            'title': 'La surrealista entrevista a la sobrina de Edmundo Arrocet: "No puedes venir aquí y tomarnos por tontos"',
            'description': 'md5:73f340a7320143d37ab895375b2bf13a',
        },
        'playlist': [{
            'md5': 'adb28c37238b675dad0f042292f209a7',
            'info_dict': {
                'id': 'TpI2EttSDAReWpJ1o0NVh2',
                'ext': 'mp4',
                'title': 'La surrealista entrevista a la sobrina de Edmundo Arrocet: "No puedes venir aquí y tomarnos por tontos"',
                'duration': 1015,
            },
        }],
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.telecinco.es/informativos/nacional/Pablo_Iglesias-Informativos_Telecinco-entrevista-Pedro_Piqueras_2_1945155182.html',
        'only_matching': True,
    }, {
        'url': 'http://www.telecinco.es/espanasinirmaslejos/Espana-gran-destino-turistico_2_1240605043.html',
        'only_matching': True,
    }, {
        'url': 'http://www.cuatro.com/chesterinlove/a-carta/chester-chester_in_love-chester_edu_2_2331030022.html',
        'only_matching': True,
    }]

    def _parse_content(self, content, url):
        video_id = content['dataMediaId']
        config = self._download_json(
            content['dataConfig'], video_id, 'Downloading config JSON')
        title = config['info']['title']
        services = config['services']
        caronte = self._download_json(services['caronte'], video_id)
        stream = caronte['dls'][0]['stream']
        headers = self.geo_verification_headers()
        headers.update({
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': re.match(r'https?://[^/]+', url).group(0),
        })
        cdn = self._download_json(
            caronte['cerbero'], video_id, data=json.dumps({
                'bbx': caronte['bbx'],
                'gbx': self._download_json(services['gbx'], video_id)['gbx'],
            }).encode(), headers=headers)['tokens']['1']['cdn']
        formats = self._extract_m3u8_formats(
            stream + '?' + cdn, video_id, 'mp4', 'm3u8_native', m3u8_id='hls')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': content.get('dataPoster') or config.get('poster', {}).get('imageUrl'),
            'duration': int_or_none(content.get('dataDuration')),
        }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        article = self._parse_json(self._search_regex(
            r'window\.\$REACTBASE_STATE\.article(?:_multisite)?\s*=\s*({.+})',
            webpage, 'article'), display_id)['article']
        title = article.get('title')
        description = clean_html(article.get('leadParagraph')) or ''
        if article.get('editorialType') != 'VID':
            entries = []
            body = [article.get('opening')]
            body.extend(try_get(article, lambda x: x['body'], list) or [])
            for p in body:
                if not isinstance(p, dict):
                    continue
                content = p.get('content')
                if not content:
                    continue
                type_ = p.get('type')
                if type_ == 'paragraph':
                    content_str = str_or_none(content)
                    if content_str:
                        description += content_str
                    continue
                if type_ == 'video' and isinstance(content, dict):
                    entries.append(self._parse_content(content, url))
            return self.playlist_result(
                entries, str_or_none(article.get('id')), title, description)
        content = article['opening']['content']
        info = self._parse_content(content, url)
        info.update({
            'description': description,
        })
        return info
