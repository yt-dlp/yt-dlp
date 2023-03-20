import itertools
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    join_nonempty,
    parse_duration,
    strftime_or_none,
    traverse_obj,
    unified_strdate,
    urljoin,
)


class RadioFranceIE(InfoExtractor):
    _VALID_URL = r'^https?://maison\.radiofrance\.fr/radiovisions/(?P<id>[^?#]+)'
    IE_NAME = 'radiofrance'

    _TEST = {
        'url': 'http://maison.radiofrance.fr/radiovisions/one-one',
        'md5': 'bdbb28ace95ed0e04faab32ba3160daf',
        'info_dict': {
            'id': 'one-one',
            'ext': 'ogg',
            'title': 'One to one',
            'description': "Plutôt que d'imaginer la radio de demain comme technologie ou comme création de contenu, je veux montrer que quelles que soient ses évolutions, j'ai l'intime conviction que la radio continuera d'être un grand média de proximité pour les auditeurs.",
            'uploader': 'Thomas Hercouët',
        },
    }

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        video_id = m.group('id')

        webpage = self._download_webpage(url, video_id)
        title = self._html_search_regex(r'<h1>(.*?)</h1>', webpage, 'title')
        description = self._html_search_regex(
            r'<div class="bloc_page_wrapper"><div class="text">(.*?)</div>',
            webpage, 'description', fatal=False)
        uploader = self._html_search_regex(
            r'<div class="credit">&nbsp;&nbsp;&copy;&nbsp;(.*?)</div>',
            webpage, 'uploader', fatal=False)

        formats_str = self._html_search_regex(
            r'class="jp-jplayer[^"]*" data-source="([^"]+)">',
            webpage, 'audio URLs')
        formats = [
            {
                'format_id': fm[0],
                'url': fm[1],
                'vcodec': 'none',
                'quality': i,
            }
            for i, fm in
            enumerate(re.findall(r"([a-z0-9]+)\s*:\s*'([^']+)'", formats_str))
        ]

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': description,
            'uploader': uploader,
        }


class RadioFranceBase(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?radiofrance\.fr'

    _STATIONS = (
        'franceculture',
        'franceinfo',
        'franceinter',
        'francemusique',
        'fip',
        'mouv',
    )


class FranceCultureIE(RadioFranceBase):
    _VALID_URL = rf'''(?x)
        {RadioFranceBase._VALID_URL_BASE}
        /(?:{"|".join(RadioFranceBase._STATIONS)})
        /podcasts/(?:[^?#]+/)?(?P<display_id>[^?#]+)-(?P<id>\d{{6,}})($|[?#])
    '''

    _TESTS = [
        {
            'url': 'https://www.radiofrance.fr/franceculture/podcasts/science-en-questions/la-physique-d-einstein-aiderait-elle-a-comprendre-le-cerveau-8440487',
            'info_dict': {
                'id': '8440487',
                'display_id': 'la-physique-d-einstein-aiderait-elle-a-comprendre-le-cerveau',
                'ext': 'mp3',
                'title': 'La physique d’Einstein aiderait-elle à comprendre le cerveau ?',
                'description': 'Existerait-il un pont conceptuel entre la physique de l’espace-temps et les neurosciences ?',
                'thumbnail': r're:^https?://.*\.(?:jpg|png)',
                'upload_date': '20220514',
                'duration': 2750,
            },
        },
        {
            'url': 'https://www.radiofrance.fr/franceinter/podcasts/le-7-9-30/le-7-9-30-du-vendredi-10-mars-2023-2107675',
            'info_dict': {
                'id': '2107675',
                'display_id': 'le-7-9-30-du-vendredi-10-mars-2023',
                'title': 'Inflation alimentaire : comment en sortir ? - Régis Debray et Claude Grange - Cybèle Idelot',
                'description': 'md5:36ee74351ede77a314fdebb94026b916',
                'thumbnail': r're:^https?://.*\.(?:jpg|png)',
                'upload_date': '20230310',
                'duration': 8977,
                'ext': 'mp3',
            },
        },
        {
            'url': 'https://www.radiofrance.fr/franceinter/podcasts/la-rafle-du-vel-d-hiv-une-affaire-d-etat/les-racines-du-crime-episode-1-3715507',
            'only_matching': True,
        }, {
            'url': 'https://www.radiofrance.fr/franceinfo/podcasts/le-billet-sciences/sante-bientot-un-vaccin-contre-l-asthme-allergique-3057200',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        webpage = self._download_webpage(url, display_id)

        # _search_json_ld doesn't correctly handle this. See https://github.com/yt-dlp/yt-dlp/pull/3874#discussion_r891903846
        video_data = self._search_json('', webpage, 'audio data', display_id, contains_pattern=r'{\s*"@type"\s*:\s*"AudioObject".+}')

        return {
            'id': video_id,
            'display_id': display_id,
            'url': video_data['contentUrl'],
            'vcodec': 'none' if video_data.get('encodingFormat') == 'mp3' else None,
            'duration': parse_duration(video_data.get('duration')),
            'title': self._html_search_regex(r'(?s)<h1[^>]*itemprop="[^"]*name[^"]*"[^>]*>(.+?)</h1>',
                                             webpage, 'title', default=self._og_search_title(webpage)),
            'description': self._html_search_regex(
                r'(?s)<meta name="description"\s*content="([^"]+)', webpage, 'description', default=None),
            'thumbnail': self._og_search_thumbnail(webpage),
            'uploader': self._html_search_regex(
                r'(?s)<span class="author">(.*?)</span>', webpage, 'uploader', default=None),
            'upload_date': unified_strdate(self._search_regex(
                r'"datePublished"\s*:\s*"([^"]+)', webpage, 'timestamp', fatal=False))
        }


class RadioFranceLiveIE(RadioFranceBase):
    _VALID_URL = rf'''(?x)
        https?://(?:www\.|embed\.)?radiofrance\.fr
        /(?P<id>{"|".join(RadioFranceBase._STATIONS)})
        (?:/player/direct)?/?(?:[#?]|$)
    '''

    _TESTS = [{
        'url': 'https://www.radiofrance.fr/franceinter/',
        'info_dict': {
            'id': 'franceinter',
            'title': str,
            'live': True,
            'ext': 'aac',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.radiofrance.fr/franceculture',
        'info_dict': {
            'id': 'franceculture',
            'title': str,
            'live': True,
            'ext': 'aac',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://embed.radiofrance.fr/franceinfo/player/direct',
        'info_dict': {
            'id': 'franceinfo',
            'title': str,
            'live': True,
            'ext': 'aac',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }]

    def _real_extract(self, url):
        station_id = self._match_id(url)

        api_response = self._download_json(
            f'https://www.radiofrance.fr/api/v2.1/stations/{station_id}/live', station_id)

        formats, subtitles = [], {}
        for media_source in api_response['now']['media']['sources']:
            if media_source.get('format') == 'hls':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(media_source['url'], station_id, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': media_source['url'],
                    'abr': media_source.get('bitrate'),
                })

        return {
            'id': station_id,
            'title': join_nonempty(
                traverse_obj(api_response, ('now', 'firstLine', 'title')),
                traverse_obj(api_response, ('now', 'secondLine', 'title')), delim=" - "),
            'formats': formats,
            'subtitles': subtitles,
            'live': True,
        }


class RadioFrancePodcastIE(RadioFranceBase):
    _VALID_URL = rf'''(?x)
        {RadioFranceBase._VALID_URL_BASE}
        /(?:{"|".join(RadioFranceBase._STATIONS)})
        /podcasts/(?P<id>[\w-]+)/?(?:[?#]|$)
    '''

    _TESTS = [{
        'url': 'https://www.radiofrance.fr/franceinfo/podcasts/le-billet-vert',
        'info_dict': {
            'id': 'eaf6ef81-a980-4f1c-a7d1-8a75ecd54b17',
            'display_id': 'le-billet-vert',
            'title': 'Le billet sciences',
            'description': 'md5:eb1007b34b0c0a680daaa71525bbd4c1',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://www.radiofrance.fr/franceinter/podcasts/jean-marie-le-pen-l-obsession-nationale',
        'info_dict': {
            'id': '566fd524-3074-4fbc-ac69-8696f2152a54',
            'display_id': 'jean-marie-le-pen-l-obsession-nationale',
            'title': 'Jean-Marie Le Pen, l\'obsession nationale',
            'description': 'md5:a07c0cfb894f6d07a62d0ad12c4b7d73',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'playlist_count': 7,
    }, {
        'url': 'https://www.radiofrance.fr/franceculture/podcasts/serie-thomas-grjebine',
        'info_dict': {
            'id': '63c1ddc9-9f15-457a-98b2-411bac63f48d',
            'display_id': 'serie-thomas-grjebine',
            'title': 'Thomas Grjebine',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.radiofrance.fr/fip/podcasts/certains-l-aiment-fip',
        'info_dict': {
            'id': '143dff38-e956-4a5d-8576-1c0b7242b99e',
            'display_id': 'certains-l-aiment-fip',
            'title': 'Certains l’aiment Fip',
            'description': 'md5:ff974672ba00d4fd5be80fb001c5b27e',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'playlist_mincount': 321,
    }, {
        'url': 'https://www.radiofrance.fr/franceinter/podcasts/le-7-9',
        'only_matching': True,
    }, {
        'url': 'https://www.radiofrance.fr/mouv/podcasts/dirty-mix',
        'only_matching': True,
    }]

    def _generate_playlist_entries(self, podcast_id, podcast_response):
        for page_num in itertools.count(2):
            for episode in podcast_response['items']:
                yield self.url_result(
                    f'https://www.radiofrance.fr/{episode["path"]}', FranceCultureIE, **traverse_obj(episode, {
                        'title': 'title',
                        'description': 'standFirst',
                        'timestamp': 'publishedDate',
                        'thumbnail': ('visual', 'src'),
                    }))

            next_cursor = podcast_response['next']
            if not next_cursor:
                break

            podcast_response = self._download_json(
                f'https://www.radiofrance.fr/api/v2.1/concepts/{podcast_id}/expressions', podcast_id,
                note=f'Downloading page {page_num}', query={'pageCursor': next_cursor})

    def _real_extract(self, url):
        display_id = self._match_id(url)

        metadata = self._download_json(
            'https://www.radiofrance.fr/api/v2.1/path', display_id,
            query={'value': urllib.parse.urlparse(url).path})['content']

        podcast_id = metadata['id']

        return self.playlist_result(
            self._generate_playlist_entries(podcast_id, metadata['expressions']), podcast_id,
            display_id=display_id, **traverse_obj(metadata, {
                'title': 'title',
                'description': 'standFirst',
                'thumbnail': ('visual', 'src'),
            }))


class RadioFranceProfileIE(RadioFranceBase):
    _VALID_URL = rf'{RadioFranceBase._VALID_URL_BASE}/personnes/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://www.radiofrance.fr/personnes/thomas-pesquet?p=3',
        'info_dict': {
            'id': '86c62790-e481-11e2-9f7b-782bcb6744eb',
            'display_id': 'thomas-pesquet',
            'title': 'Thomas Pesquet',
            'description': 'Astronaute à l\'agence spatiale européenne',
        },
        'playlist_mincount': 212,
    }, {
        'url': 'https://www.radiofrance.fr/personnes/lea-salame',
        'only_matching': True,
    }]

    def _generate_playlist_entries(self, profile_id, profile_response):
        for page_num in itertools.count(2):
            for entry in profile_response['items']:
                yield self.url_result(
                    f'https://www.radiofrance.fr/{entry["path"]}', **traverse_obj(entry, {
                        'title': 'title',
                        'description': 'standFirst',
                        'timestamp': 'publishedDate',
                        'thumbnail': ('visual', 'src'),
                    }))

            next_cursor = profile_response['pagination']['next']
            if not next_cursor:
                break

            profile_response = self._download_json(
                f'https://www.radiofrance.fr/api/v2.1/taxonomy/{profile_id}/documents', profile_id,
                note=f'Downloading page {page_num}', query={
                    'relation': 'personality',
                    'cursor': next_cursor
                })

    def _real_extract(self, url):
        display_id = self._match_id(url)

        metadata = self._download_json(
            'https://www.radiofrance.fr/api/v2.1/path', display_id,
            query={'value': urllib.parse.urlparse(url).path})['content']

        profile_id = metadata['id']

        return self.playlist_result(
            self._generate_playlist_entries(profile_id, metadata['documents']), profile_id,
            display_id=display_id, **traverse_obj(metadata, {
                'title': 'name',
                'description': 'role',
                'thumbnail': ('visual', 'src'),
            }))


class RadioFranceProgramScheduleIE(RadioFranceBase):
    _VALID_URL = rf'''(?x)
        {RadioFranceBase._VALID_URL_BASE}
        /(?P<station>{"|".join(RadioFranceBase._STATIONS)})
        /grille-programmes(?:\?date=(?P<date>[\d-]+))?
    '''

    _TESTS = [{
        'url': 'https://www.radiofrance.fr/franceinter/grille-programmes?date=17-02-2023',
        'info_dict': {
            'id': 'franceinter-program-20230217',
            'upload_date': '20230217',
        },
        'playlist_count': 25,
    }, {
        'url': 'https://www.radiofrance.fr/franceculture/grille-programmes?date=01-02-2023',
        'info_dict': {
            'id': 'franceculture-program-20230201',
            'upload_date': '20230201',
        },
        'playlist_count': 25,
    }, {
        'url': 'https://www.radiofrance.fr/mouv/grille-programmes?date=19-03-2023',
        'info_dict': {
            'id': 'mouv-program-20230319',
            'upload_date': '20230319',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://www.radiofrance.fr/francemusique/grille-programmes?date=18-03-2023',
        'info_dict': {
            'id': 'francemusique-program-20230318',
            'upload_date': '20230318',
        },
        'playlist_count': 15,
    }, {
        'url': 'https://www.radiofrance.fr/franceculture/grille-programmes',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        station, date = self._match_valid_url(url).group('station', 'date')

        api_response = self._download_json(
            f'https://www.radiofrance.fr/api/v2.1/stations/{station}/programs', f'{station}-program',
            query={'date': date} if date is not None else {})

        entries = []
        for entry in api_response['steps']:
            path = traverse_obj(entry, ('expression', 'path'))
            if path is None:
                continue

            entries.append(self.url_result(
                urljoin(url, f'/{path}'), ie=FranceCultureIE, **traverse_obj(entry, {
                    'title': ('expression', 'title'),
                    'thumbnail': ('expression', 'visual', 'src'),
                    'timestamp': 'startTime',
                    'series_id': ('concept', 'id'),
                    'series': ('concept', 'title'),
                })))

        upload_date = strftime_or_none(api_response.get('date'), '%Y%m%d')
        return self.playlist_result(entries, join_nonempty(station, 'program', upload_date), upload_date=upload_date)
