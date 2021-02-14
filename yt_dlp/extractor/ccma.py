# coding: utf-8
from __future__ import unicode_literals

import datetime
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_duration,
    parse_resolution,
    try_get,
    url_or_none,
)


class CCMAIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ccma\.cat/(?:[^/]+/)*?(?P<type>video|audio)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.ccma.cat/tv3/alacarta/lespot-de-la-marato-de-tv3/lespot-de-la-marato-de-tv3/video/5630208/',
        'md5': '7296ca43977c8ea4469e719c609b0871',
        'info_dict': {
            'id': '5630208',
            'ext': 'mp4',
            'title': 'L\'espot de La Marató de TV3',
            'description': 'md5:f12987f320e2f6e988e9908e4fe97765',
            'timestamp': 1478608140,
            'upload_date': '20161108',
            'age_limit': 0,
        }
    }, {
        'url': 'http://www.ccma.cat/catradio/alacarta/programa/el-consell-de-savis-analitza-el-derbi/audio/943685/',
        'md5': 'fa3e38f269329a278271276330261425',
        'info_dict': {
            'id': '943685',
            'ext': 'mp3',
            'title': 'El Consell de Savis analitza el derbi',
            'description': 'md5:e2a3648145f3241cb9c6b4b624033e53',
            'upload_date': '20170512',
            'timestamp': 1494622500,
            'vcodec': 'none',
            'categories': ['Esports'],
        }
    }, {
        'url': 'http://www.ccma.cat/tv3/alacarta/crims/crims-josep-tallada-lespereu-me-capitol-1/video/6031387/',
        'md5': 'b43c3d3486f430f3032b5b160d80cbc3',
        'info_dict': {
            'id': '6031387',
            'ext': 'mp4',
            'title': 'Crims - Josep Talleda, l\'"Espereu-me" (capítol 1)',
            'description': 'md5:7cbdafb640da9d0d2c0f62bad1e74e60',
            'timestamp': 1582577700,
            'upload_date': '20200224',
            'subtitles': 'mincount:4',
            'age_limit': 16,
            'series': 'Crims',
        }
    }]

    def _real_extract(self, url):
        media_type, media_id = re.match(self._VALID_URL, url).groups()

        media = self._download_json(
            'http://dinamics.ccma.cat/pvideo/media.jsp', media_id, query={
                'media': media_type,
                'idint': media_id,
            })

        formats = []
        media_url = media['media']['url']
        if isinstance(media_url, list):
            for format_ in media_url:
                format_url = url_or_none(format_.get('file'))
                if not format_url:
                    continue
                label = format_.get('label')
                f = parse_resolution(label)
                f.update({
                    'url': format_url,
                    'format_id': label,
                })
                formats.append(f)
        else:
            formats.append({
                'url': media_url,
                'vcodec': 'none' if media_type == 'audio' else None,
            })
        self._sort_formats(formats)

        informacio = media['informacio']
        title = informacio['titol']
        durada = informacio.get('durada') or {}
        duration = int_or_none(durada.get('milisegons'), 1000) or parse_duration(durada.get('text'))
        tematica = try_get(informacio, lambda x: x['tematica']['text'])

        timestamp = None
        data_utc = try_get(informacio, lambda x: x['data_emissio']['utc'])
        try:
            timestamp = datetime.datetime.strptime(
                data_utc, '%Y-%d-%mT%H:%M:%S%z').timestamp()
        except TypeError:
            pass

        subtitles = {}
        subtitols = media.get('subtitols') or []
        if isinstance(subtitols, dict):
            subtitols = [subtitols]
        for st in subtitols:
            sub_url = st.get('url')
            if sub_url:
                subtitles.setdefault(
                    st.get('iso') or st.get('text') or 'ca', []).append({
                        'url': sub_url,
                    })

        thumbnails = []
        imatges = media.get('imatges', {})
        if imatges:
            thumbnail_url = imatges.get('url')
            if thumbnail_url:
                thumbnails = [{
                    'url': thumbnail_url,
                    'width': int_or_none(imatges.get('amplada')),
                    'height': int_or_none(imatges.get('alcada')),
                }]

        age_limit = None
        codi_etic = try_get(informacio, lambda x: x['codi_etic']['id'])
        if codi_etic:
            codi_etic_s = codi_etic.split('_')
            if len(codi_etic_s) == 2:
                if codi_etic_s[1] == 'TP':
                    age_limit = 0
                else:
                    age_limit = int_or_none(codi_etic_s[1])

        return {
            'id': media_id,
            'title': title,
            'description': clean_html(informacio.get('descripcio')),
            'duration': duration,
            'timestamp': timestamp,
            'thumbnails': thumbnails,
            'subtitles': subtitles,
            'formats': formats,
            'age_limit': age_limit,
            'alt_title': informacio.get('titol_complet'),
            'episode_number': int_or_none(informacio.get('capitol')),
            'categories': [tematica] if tematica else None,
            'series': informacio.get('programa'),
        }
