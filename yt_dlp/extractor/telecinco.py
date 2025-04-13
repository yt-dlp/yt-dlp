import json
import re

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    join_nonempty,
    str_or_none,
    traverse_obj,
    update_url,
    url_or_none,
)


class TelecincoBaseIE(InfoExtractor):
    def _parse_content(self, content, url):
        video_id = content['dataMediaId']
        config = self._download_json(
            content['dataConfig'], video_id, 'Downloading config JSON')
        services = config['services']
        caronte = self._download_json(services['caronte'], video_id)
        if traverse_obj(caronte, ('dls', 0, 'drm', {bool})):
            self.report_drm(video_id)

        stream = caronte['dls'][0]['stream']
        headers = {
            'Referer': url,
            'Origin': re.match(r'https?://[^/]+', url).group(0),
        }
        geo_headers = {**headers, **self.geo_verification_headers()}

        try:
            cdn = self._download_json(
                caronte['cerbero'], video_id, data=json.dumps({
                    'bbx': caronte['bbx'],
                    'gbx': self._download_json(services['gbx'], video_id)['gbx'],
                }).encode(), headers={
                    'Content-Type': 'application/json',
                    **geo_headers,
                })['tokens']['1']['cdn']
        except ExtractorError as error:
            if isinstance(error.cause, HTTPError) and error.cause.status == 403:
                error_code = traverse_obj(
                    self._webpage_read_content(error.cause.response, caronte['cerbero'], video_id, fatal=False),
                    ({json.loads}, 'code', {int}))
                if error_code in (4038, 40313):
                    self.raise_geo_restricted(countries=['ES'])
            raise

        formats = self._extract_m3u8_formats(
            update_url(stream, query=cdn), video_id, 'mp4', m3u8_id='hls', headers=geo_headers)

        return {
            'id': video_id,
            'title': traverse_obj(config, ('info', 'title', {str})),
            'formats': formats,
            'thumbnail': (traverse_obj(content, ('dataPoster', {url_or_none}))
                          or traverse_obj(config, 'poster', 'imageUrl', expected_type=url_or_none)),
            'duration': traverse_obj(content, ('dataDuration', {int_or_none})),
            'http_headers': headers,
        }


class TelecincoIE(TelecincoBaseIE):
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
        'skip': 'HTTP Error 410 Gone',
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
        'skip': 'Redirects to main page',
    }, {
        'url': 'http://www.mediaset.es/12meses/campanas/doylacara/conlatratanohaytrato/Ayudame-dar-cara-trata-trato_2_1986630220.html',
        'md5': '5ce057f43f30b634fbaf0f18c71a140a',
        'info_dict': {
            'id': 'aywerkD2Sv1vGNqq9b85Q2',
            'ext': 'mp4',
            'title': '#DOYLACARA. Con la trata no hay trato',
            'duration': 50,
            'thumbnail': 'https://album.mediaset.es/eimg/2017/11/02/1tlQLO5Q3mtKT24f3EaC24.jpg',
        },
    }, {
        # video in opening's content
        'url': 'https://www.telecinco.es/vivalavida/fiorella-sobrina-edmundo-arrocet-entrevista_18_2907195140.html',
        'info_dict': {
            'id': '1691427',
            'title': 'La surrealista entrevista a la sobrina de Edmundo Arrocet: "No puedes venir aquí y tomarnos por tontos"',
            'description': r're:Fiorella, la sobrina de Edmundo Arrocet, concedió .{727}',
        },
        'playlist': [{
            'md5': 'adb28c37238b675dad0f042292f209a7',
            'info_dict': {
                'id': 'TpI2EttSDAReWpJ1o0NVh2',
                'ext': 'mp4',
                'title': 'La surrealista entrevista a la sobrina de Edmundo Arrocet: "No puedes venir aquí y tomarnos por tontos"',
                'duration': 1015,
                'thumbnail': 'https://album.mediaset.es/eimg/2020/02/29/5opaC37lUhKlZ7FoDhiVC.jpg',
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

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        article = self._search_json(
            r'window\.\$REACTBASE_STATE\.article(?:_multisite)?\s*=',
            webpage, 'article', display_id)['article']
        description = traverse_obj(article, ('leadParagraph', {clean_html}, filter))

        if article.get('editorialType') != 'VID':
            entries = []

            for p in traverse_obj(article, ((('opening', all), 'body'), lambda _, v: v['content'])):
                content = p['content']
                type_ = p.get('type')
                if type_ == 'paragraph' and isinstance(content, str):
                    description = join_nonempty(description, content, delim='')
                elif type_ == 'video' and isinstance(content, dict):
                    entries.append(self._parse_content(content, url))

            return self.playlist_result(
                entries, str_or_none(article.get('id')),
                traverse_obj(article, ('title', {str})), clean_html(description))

        info = self._parse_content(article['opening']['content'], url)
        info['description'] = description
        return info
