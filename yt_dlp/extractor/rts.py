import functools

from .srgssr import SRGSSRIE
from ..utils import (
    determine_ext,
    int_or_none,
    orderedSet,
    parse_iso8601,
    parse_resolution,
)
from ..utils.traversal import traverse_obj


class RTSIE(SRGSSRIE):
    _GEO_COUNTRIES = ['CH']
    IE_DESC = 'RTS.ch'
    _VALID_URL = [
        r'rts:(?P<id>\d+)',
        r'https?://(?:.+?\.)?rts\.ch/(?:[^/]+/){2,}(?P<id>[0-9]+)-(?P<display_id>.+?)\.html',
        r'https?://(?:.+?\.)?rts\.ch/(?:[^/]+/){2,}(?P<display_id>.+?)-(?P<id>[0-9]+)\.html',
    ]

    _TESTS = [
        {
            # article with videos
            'url': 'http://www.rts.ch/archives/tv/divers/3449373-les-enfants-terribles.html',
            'info_dict': {
                'id': '3449373',
                'title': 'Les Enfants Terribles',
                'description': 'France Pommier et sa soeur Luce Feral, les deux filles de ce groupe de 5.',
                'display_id': 'les-enfants-terribles',
                'tags': ['Divers', 'Archives TV', 'Culture et Arts', 'Les archives', 'Personnalités', 'RTS Archives', 'Années 1960', 'Autres arts', 'Décennies', 'Société'],
            },
            'playlist': [{
                'info_dict': {
                    'id': '3449373',
                    'ext': 'mp4',
                    'title': 'Les Enfants Terribles',
                    'description': 'France Pommier et sa soeur Luce Feral, les deux filles de ce groupe de 5.',
                    'thumbnail': r're:^https?://.*\.image',
                    'upload_date': '19680921',
                    'timestamp': -40280400,
                    'duration': 1488,
                    'categories': ['Divers'],
                },
            }],
            'params': {'skip_download': 'm3u8'},  # 700-byte first fragment
        },
        {
            # video without text content
            'url': 'http://www.rts.ch/video/sport/hockey/5745975-1-2-kloten-fribourg-5-2-second-but-pour-gotteron-par-kwiatowski.html',
            'info_dict': {
                'id': '5745975',
                'display_id': '1-2-kloten-fribourg-5-2-second-but-pour-gotteron-par-kwiatowski',
                'title': '1/2, Kloten - Fribourg (5-2): second but pour Gottéron par Kwiatowski',
                'description': 'Hockey - Playoff',
                'tags': ['Hockey', 'Sport', 'RTS Sport'],
            },
            'playlist': [{
                'info_dict': {
                    'id': '5745975',
                    'ext': 'mp4',
                    'title': '1/2, Kloten - Fribourg (5-2): second but pour Gottéron par Kwiatowski',
                    'description': 'Hockey - Playoff',
                    'thumbnail': r're:^https?://.*\.image',
                    'upload_date': '20140403',
                    'timestamp': 1396556882,
                    'duration': 48,
                    'categories': ['Hockey sur glace'],
                },
            }],
            'params': {'skip_download': 'm3u8'},  # 700-byte first fragment
            'skip': 'Blocked outside Switzerland',
        },
        {
            # video player; redirection: https://www.rts.ch/play/tv/lactu-en-video/video/londres-cachee-par-un-epais-smog?urn=urn:rts:video:5745356
            'url': 'http://www.rts.ch/video/info/journal-continu/5745356-londres-cachee-par-un-epais-smog.html',
            'info_dict': {
                'id': '5745356',
                'ext': 'mp4',
                'duration': 33.76,
                'title': 'Londres cachée par un épais smog',
                'description': 'Un important voile de smog recouvre Londres depuis mercredi, provoqué par la pollution et du sable du Sahara.',
                'upload_date': '20140403',
                'timestamp': 1396537322,
                'thumbnail': r're:^https?://.*\.image',
                'webpage_url': 'srgssr:rts:video:5745356',
            },
            'params': {'skip_download': 'm3u8'},  # 700-byte first fragment
        },
        {
            # audio & podcast
            'url': 'http://www.rts.ch/audio/couleur3/programmes/la-belle-video-de-stephane-laurenceau/5706148-urban-hippie-de-damien-krisl-03-04-2014.html',
            'info_dict': {
                'id': '5706148',
                'title': '"Urban Hippie", de Damien Krisl',
                'description': 'Des Hippies super glam.',
                'display_id': 'urban-hippie-de-damien-krisl',
                'tags': ['Media Radio', 'Couleur3'],
            },
            'playlist': [{
                'info_dict': {
                    'id': '5706148',
                    'ext': 'mp3',
                    'title': '"Urban Hippie", de Damien Krisl',
                    'description': 'Des Hippies super glam.',
                    'thumbnail': r're:^https?://.*\.image',
                    'upload_date': '20140403',
                    'timestamp': 1396546481,
                    'duration': 123,
                    'categories': ['La belle vidéo de Stéphane Laurenceau'],
                },
            }, {
                'info_dict': {
                    'id': '5747185',
                    'ext': 'mp3',
                    'title': 'Le musée du psychédélisme',
                    'description': 'md5:72f8662f48c32050ae817e3bde7e0acc',
                    'thumbnail': r're:^https?://.*\.image',
                    'upload_date': '20140402',
                    'timestamp': 1396476000,
                    'duration': 274,
                    'categories': ['Happy Culture'],
                },
            }, {
                'info_dict': {
                    'id': '5706149',
                    'ext': 'mp3',
                    'title': 'Silk Art Hippie Culture',
                    'description': 'md5:8e3b9d8d84d85ca8a1905cf50b39bba4',
                    'thumbnail': r're:^https?://.*\.image',
                    'upload_date': '20140403',
                    'timestamp': 1396545649,
                    'duration': 161,
                    'categories': ['Happy Pics'],
                },
            }, {
                'info_dict': {
                    'id': '5706148',
                    'ext': 'mp3',
                    'title': '"Urban Hippie", de Damien Krisl',
                    'description': 'Des Hippies super glam.',
                    'thumbnail': r're:^https?://.*\.image',
                    'upload_date': '20140403',
                    'timestamp': 1396546481,
                    'duration': 123,
                    'categories': ['La belle vidéo de Stéphane Laurenceau'],
                },
            }],
        },
        {
            # article with videos on rhs
            'url': 'http://www.rts.ch/sport/hockey/6693917-hockey-davos-decroche-son-31e-titre-de-champion-de-suisse.html',
            'info_dict': {
                'id': '6693917',
                'title': 'Davos décroche le 31e titre de son histoire',
                'description': 'md5:3c9a767b2a332413eda33c526024578c',
                'display_id': 'hockey-davos-decroche-son-31e-titre-de-champion-de-suisse',
                'tags': ['Hockey', 'Tout le sport', 'RTS Info', 'LNA', "Toute l'info", 'RTS Sport'],
            },
            'playlist_mincount': 5,
            'skip': 'Blocked outside Switzerland',
        },
        {
            # articles containing recordings of TV shows
            'url': 'https://www.rts.ch/info/regions/valais/12865814-un-bouquetin-emporte-par-un-aigle-royal-sur-les-hauts-de-fully-vs.html',
            'info_dict': {
                'id': '12865814',
                'title': 'Un bouquetin emporté par un aigle royal sur les hauts de Fully (VS)',
                'description': 'md5:9b511f89075e2730bd2dd59915c25574',
                'display_id': 'un-bouquetin-emporte-par-un-aigle-royal-sur-les-hauts-de-fully-vs',
                'tags': ['Régions', 'RTS Info', 'Valais', "Toute l'info"],
            },
            'playlist': [{
                'info_dict': {
                    'id': '12861415',
                    'ext': 'mp4',
                    'title': 'En Valais, un bouquetin emporté dans les airs par un aigle royal. Décryptage d’une image rare.',
                    'thumbnail': r're:^https?://.*\.image',
                    'timestamp': 1644690600,
                    'upload_date': '20220212',
                    'duration': 107,
                    'categories': ['19h30'],
                },
            }],
            'params': {'skip_download': 'm3u8'},  # 700-byte first fragment
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        },
        {
            # new URL format; article with videos
            'url': 'https://www.rts.ch/info/suisse/2024/article/doris-leuthard-il-y-a-des-alternatives-au-nucleaire-qui-sont-moins-risquees-28631869.html',
            'info_dict': {
                'id': '28631869',
                'title': 'Doris Leuthard: "Il y a des alternatives au nucléaire qui sont moins risquées"',
                'description': 'md5:ba9930e218dcd177801a34b89a16b86e',
                'display_id': 'doris-leuthard-il-y-a-des-alternatives-au-nucleaire-qui-sont-moins-risquees',
                'tags': 'count:13',
            },
            'playlist': [{
                'info_dict': {
                    'id': '15162786',
                    'ext': 'mp4',
                    'title': 'L\'invitée de La Matinale (vidéo) - Doris Leuthard, co-présidente du projet d\'exposition nationale Svizra27',
                    'thumbnail': r're:^https?://.*\.image',
                    'upload_date': '20240916',
                    'timestamp': 1726462800,
                    'duration': 860,
                    'categories': ['La Matinale'],
                },
            }, {
                'info_dict': {
                    'id': '15164848',
                    'ext': 'mp4',
                    'title': 'Le Centre pourrait faire pencher la balance en faveur de la construction de nouvelles centrales nucléaires',
                    'thumbnail': r're:^https?://.*\.image',
                    'upload_date': '20240916',
                    'timestamp': 1726502400,
                    'duration': 227,
                    'categories': ['Forum'],
                },
            }],
            'params': {'skip_download': 'm3u8'},  # 700-byte first fragment
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        },
        {
            'url': 'http://pages.rts.ch/emissions/passe-moi-les-jumelles/5624065-entre-ciel-et-mer.html',
            'only_matching': True,
        },
        {
            'url': 'http://www.rts.ch/emissions/passe-moi-les-jumelles/5624067-entre-ciel-et-mer.html',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        webpage, urlh = self._download_webpage_handle(url, self._match_id(url))
        if urlh.url != url:
            return self.url_result(urlh.url)

        mobj = self._match_valid_url(url)
        display_id = traverse_obj(mobj, 'display_id', default=mobj.group('id')) or mobj.group('id')

        media_list = []
        article_details = self._search_json(r'articleDetails\s*=\s*', webpage, 'article details', display_id)
        traverse_obj(article_details, ('mainMedia', {lambda x: media_list.append(x) if x else None}))
        traverse_obj(article_details, ('innerMediaElements', {lambda x: media_list.extend(x)}))
        traverse_obj(article_details, ('mediaElements', {lambda x: media_list.extend(x)}))
        media_list = orderedSet(media_list)

        entries = []
        for media in media_list:
            media_id = media['oid']
            media_info = self._get_media_data('rts', media['type'], media_id)

            if fmts := self._extract_formats(media_info, media_id):
                entries.append({
                    'id': media_info['id'],
                    'title': media_info['title'],
                    'formats': fmts,
                    'description': media_info.get('description'),
                    'thumbnails': [traverse_obj(media_info, ('imageUrl', {lambda x: {
                        'url': x,
                        **parse_resolution(x),
                    }}))],
                    'timestamp': parse_iso8601(media_info.get('date')),
                    'duration': traverse_obj(media_info, ('duration', {functools.partial(int_or_none, scale=1000)})),
                    'categories': [media.get('category')],
                })

        return self.playlist_result(
            entries, article_details.get('oid'), article_details.get('title'),
            article_details.get('lead'), display_id=display_id,
            tags=traverse_obj(article_details, ('tags', ..., 'name')))

    def _extract_formats(self, media_info, media_id):
        def extract_bitrate(url):
            return int_or_none(self._search_regex(
                r'-([0-9]+)k\.', url, 'bitrate', default=None))

        formats = []
        for idx, stream in enumerate(traverse_obj(
                media_info, ('resourceList', lambda _, v: v['url']))):
            format_id = stream.get('protocol') or str(idx)
            format_url = stream['url']
            if format_id == 'hds_sd' and 'hds' in stream:
                continue
            if format_id == 'hls_sd' and 'hls' in stream:
                continue
            ext = determine_ext(format_url)
            if ext in ('m3u8', 'f4m'):
                format_url = self._get_tokenized_src(format_url, media_id, format_id)
                if ext == 'f4m':
                    formats.extend(self._extract_f4m_formats(
                        format_url + ('?' if '?' not in format_url else '&') + 'hdcore=3.4.0',
                        media_id, f4m_id=format_id, fatal=False))
                else:
                    formats.extend(self._extract_m3u8_formats(
                        format_url, media_id, 'mp4', 'm3u8_native', m3u8_id=format_id, fatal=False))
            else:
                formats.append({
                    'format_id': format_id,
                    'url': format_url,
                    'tbr': extract_bitrate(format_url),
                })

        self._check_formats(formats, media_id)
        return formats
