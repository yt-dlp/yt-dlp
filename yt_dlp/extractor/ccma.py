from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    parse_duration,
    parse_resolution,
    try_get,
    unified_timestamp,
    url_or_none,
)


class CCMAIE(InfoExtractor):
    IE_DESC = '3Cat, TV3 and Catalunya Ràdio'
    _VALID_URL = r'https?://(?:www\.)?3cat\.cat/(?:3cat|tv3/sx3)/[^/?#]+/(?P<type>video|audio)/(?P<id>\d+)'
    _TESTS = [{
        # ccma.cat/tv3/alacarta/ URLs redirect to 3cat.cat/3cat/
        'url': 'https://www.3cat.cat/3cat/lespot-de-la-marato-de-tv3/video/5630208/',
        'md5': '7296ca43977c8ea4469e719c609b0871',
        'info_dict': {
            'id': '5630208',
            'ext': 'mp4',
            'title': 'L\'espot de La Marató 2016: Ictus i les lesions medul·lars i cerebrals traumàtiques',
            'description': 'md5:f12987f320e2f6e988e9908e4fe97765',
            'timestamp': 1478608140,
            'upload_date': '20161108',
            'age_limit': 0,
            'alt_title': 'EsportMarató2016WEB_PerPublicar',
            'duration': 79,
            'thumbnail': 'https://img.3cat.cat/multimedia/jpg/4/6/1478536106664.jpg',
            'series': 'Dedicada a l\'ictus i les lesions medul·lars i cerebrals traumàtiques',
            'categories': ['Divulgació'],
        },
    }, {
        # ccma.cat/catradio/alacarta/ URLs redirect to 3cat.cat/3cat/
        'url': 'https://www.3cat.cat/3cat/el-consell-de-savis-analitza-el-derbi/audio/943685/',
        'md5': 'fa3e38f269329a278271276330261425',
        'info_dict': {
            'id': '943685',
            'ext': 'mp3',
            'title': 'El Consell de Savis analitza el derbi',
            'description': 'md5:e2a3648145f3241cb9c6b4b624033e53',
            'upload_date': '20161217',
            'timestamp': 1482011700,
            'vcodec': 'none',
            'categories': ['Esports'],
            'series': 'Tot gira',
            'duration': 821,
            'thumbnail': 'https://img.3cat.cat/multimedia/jpg/8/9/1482002602598.jpg',
        },
    }, {
        'url': 'https://www.3cat.cat/3cat/crims-josep-tallada-lespereu-me-part-1/video/6031387/',
        'md5': '27493513d08a3e5605814aee9bb778d2',
        'info_dict': {
            'id': '6031387',
            'ext': 'mp4',
            'title': 'T1xC5 - Josep Talleda, l\'"Espereu-me" (part 1)',
            'description': 'md5:7cbdafb640da9d0d2c0f62bad1e74e60',
            'timestamp': 1582577919,
            'upload_date': '20200224',
            'subtitles': 'mincount:1',
            'age_limit': 13,
            'series': 'Crims',
            'thumbnail': 'https://img.3cat.cat/multimedia/jpg/1/9/1582564376991.jpg',
            'duration': 3203,
            'categories': ['Divulgació'],
            'alt_title': 'Crims - 5 - Josep Talleda, l\'"Espereu-me" (1a part) - Josep Talleda, l\'"Espereu-me" (part 1)',
            'episode_number': 5,
            'episode': 'Episode 5',
        },
    }, {
        'url': 'https://www.3cat.cat/tv3/sx3/una-mosca-volava-per-la-llum/video/5759227/',
        'info_dict': {
            'id': '5759227',
            'ext': 'mp4',
            'title': 'Una mosca volava per la llum',
            'alt_title': '17Z004Ç UNA MOSCA VOLAVA PER LA LLUM',
            'description': 'md5:9ab64276944b0825336f4147f13f7854',
            'series': 'Mic',
            'upload_date': '20180411',
            'timestamp': 1523440105,
            'duration': 160,
            'age_limit': 0,
            'thumbnail': 'https://img.3cat.cat/multimedia/jpg/6/1/1524071667216.jpg',
            'categories': ['Música'],
        },
    }]

    def _real_extract(self, url):
        media_type, media_id = self._match_valid_url(url).group('type', 'id')

        media = self._download_json(
            'http://api-media.3cat.cat/pvideo/media.jsp', media_id, query={
                'media': media_type,
                'idint': media_id,
                'format': 'dm',
            })

        formats = []
        media_url = media['media']['url']
        if isinstance(media_url, list):
            for format_ in media_url:
                format_url = url_or_none(format_.get('file'))
                if not format_url:
                    continue
                if determine_ext(format_url) == 'mpd':
                    formats.extend(self._extract_mpd_formats(
                        format_url, media_id, mpd_id='dash', fatal=False))
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

        informacio = media['informacio']
        title = informacio['titol']
        durada = informacio.get('durada') or {}
        duration = int_or_none(durada.get('milisegons'), 1000) or parse_duration(durada.get('text'))
        tematica = try_get(informacio, lambda x: x['tematica']['text'])

        data_utc = try_get(informacio, lambda x: x['data_emissio']['utc'])
        timestamp = unified_timestamp(data_utc)

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
