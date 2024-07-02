import itertools
import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    join_nonempty,
    js_to_json,
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


class RadioFranceBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?radiofrance\.fr'

    _STATIONS_RE = '|'.join(map(re.escape, (
        'franceculture',
        'franceinfo',
        'franceinter',
        'francemusique',
        'fip',
        'mouv',
    )))

    def _extract_data_from_webpage(self, webpage, display_id, key):
        return traverse_obj(self._search_json(
            r'\bconst\s+data\s*=', webpage, key, display_id,
            contains_pattern=r'\[\{(?s:.+)\}\]', transform_source=js_to_json),
            (..., 'data', key, {dict}), get_all=False) or {}


class FranceCultureIE(RadioFranceBaseIE):
    _VALID_URL = rf'''(?x)
        {RadioFranceBaseIE._VALID_URL_BASE}
        /(?:{RadioFranceBaseIE._STATIONS_RE})
        /podcasts/(?:[^?#]+/)?(?P<display_id>[^?#]+)-(?P<id>\d{{6,}})(?:$|[?#])
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
        },
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
                r'"datePublished"\s*:\s*"([^"]+)', webpage, 'timestamp', fatal=False)),
        }


class RadioFranceLiveIE(RadioFranceBaseIE):
    _VALID_URL = rf'''(?x)
        https?://(?:www\.)?radiofrance\.fr
        /(?P<id>{RadioFranceBaseIE._STATIONS_RE})
        /?(?P<substation_id>radio-[\w-]+)?(?:[#?]|$)
    '''

    _TESTS = [{
        'url': 'https://www.radiofrance.fr/franceinter/',
        'info_dict': {
            'id': 'franceinter',
            'title': str,
            'live_status': 'is_live',
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
            'live_status': 'is_live',
            'ext': 'aac',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.radiofrance.fr/mouv/radio-musique-kids-family',
        'info_dict': {
            'id': 'mouv-radio-musique-kids-family',
            'title': str,
            'live_status': 'is_live',
            'ext': 'aac',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.radiofrance.fr/mouv/radio-rnb-soul',
        'info_dict': {
            'id': 'mouv-radio-rnb-soul',
            'title': str,
            'live_status': 'is_live',
            'ext': 'aac',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.radiofrance.fr/mouv/radio-musique-mix',
        'info_dict': {
            'id': 'mouv-radio-musique-mix',
            'title': str,
            'live_status': 'is_live',
            'ext': 'aac',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.radiofrance.fr/fip/radio-rock',
        'info_dict': {
            'id': 'fip-radio-rock',
            'title': str,
            'live_status': 'is_live',
            'ext': 'aac',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.radiofrance.fr/mouv',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        station_id, substation_id = self._match_valid_url(url).group('id', 'substation_id')

        if substation_id:
            webpage = self._download_webpage(url, station_id)
            api_response = self._search_json(r'webradioLive:\s*', webpage, station_id, substation_id,
                                             transform_source=js_to_json)
        else:
            api_response = self._download_json(
                f'https://www.radiofrance.fr/{station_id}/api/live', station_id)

        formats, subtitles = [], {}
        for media_source in traverse_obj(api_response, (('now', None), 'media', 'sources', lambda _, v: v['url'])):
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
            'id': join_nonempty(station_id, substation_id),
            'title': traverse_obj(api_response, ('visual', 'legend')) or join_nonempty(
                ('now', 'firstLine', 'title'), ('now', 'secondLine', 'title'), from_dict=api_response, delim=' - '),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
        }


class RadioFrancePlaylistBaseIE(RadioFranceBaseIE):
    """Subclasses must set _METADATA_KEY"""

    def _call_api(self, station, content_id, cursor):
        raise NotImplementedError('This method must be implemented by subclasses')

    def _generate_playlist_entries(self, station, content_id, content_response):
        for page_num in itertools.count(2):
            for entry in content_response['items']:
                yield self.url_result(
                    f'https://www.radiofrance.fr/{entry["path"]}', url_transparent=True, **traverse_obj(entry, {
                        'title': 'title',
                        'description': 'standFirst',
                        'timestamp': ('publishedDate', {int_or_none}),
                        'thumbnail': ('visual', 'src'),
                    }))

            if not content_response['next']:
                break

            content_response = self._call_api(station, content_id, content_response['next'])

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        # If it is a podcast playlist, get the name of the station it is on
        # profile page playlists are not attached to a station currently
        station = self._match_valid_url(url).group('station') if isinstance(self, RadioFrancePodcastIE) else None

        # Get data for the first page, and the uuid for the playlist
        metadata = self._call_api(station, playlist_id, 1)
        uuid = traverse_obj(metadata, ('metadata', 'id'))

        return self.playlist_result(
            self._generate_playlist_entries(station, playlist_id, metadata),
            uuid,
            display_id=playlist_id,
            **{**traverse_obj(metadata['metadata'], {
                'title': 'title',
                'description': 'standFirst',
                'thumbnail': ('visual', 'src'),
            }), **traverse_obj(metadata['metadata'], {
                'title': 'name',
                'description': 'role',
            })})


class RadioFrancePodcastIE(RadioFrancePlaylistBaseIE):
    _VALID_URL = rf'''(?x)
        {RadioFranceBaseIE._VALID_URL_BASE}
        /(?P<station>{RadioFranceBaseIE._STATIONS_RE})
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
        'url': 'https://www.radiofrance.fr/franceinter/podcasts/avec-la-langue',
        'info_dict': {
            'id': '53a95989-7c61-48c7-873c-6a71009101bb',
            'display_id': 'avec-la-langue',
            'title': 'Avec la langue',
            'description': 'md5:4ddb6d4ed46dbbdee611b8e16e4af868',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'playlist_mincount': 36,
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
            'description': 'md5:7c373cdcec7a024f12fa34de7612e44e',
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

    _METADATA_KEY = 'expressions'

    def _call_api(self, station, podcast_id, cursor):
        # The data is stored in the last <script> tag on a page
        url = 'https://www.radiofrance.fr/' + station + '/podcasts/' + podcast_id + '?p=' + str(cursor)
        webpage = self._download_webpage(url, podcast_id, note=f'Downloading {podcast_id} page {cursor}')

        resp = dict()

        # _search_json cannot parse the data as it contains javascript
        # Therefore, parse the episodes objects array separately
        resp['items'] = self._search_json(r'a.items\s*=\s*', webpage, podcast_id, podcast_id,
                                          contains_pattern=r'\[.+\]', transform_source=js_to_json)

        # the pagination data is stored in a javascript object 'a'
        lastPage = int(re.search(r'a\.lastPage\s*=\s*(\d+);', webpage).group(1))
        hasMorePages = cursor < lastPage
        resp['next'] = cursor + 1 if hasMorePages else None

        resp['metadata'] = self._search_json(r'content:\s*', webpage, podcast_id, podcast_id,
                                             transform_source=js_to_json)

        return resp


class RadioFranceProfileIE(RadioFrancePlaylistBaseIE):
    _VALID_URL = rf'{RadioFranceBaseIE._VALID_URL_BASE}/personnes/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://www.radiofrance.fr/personnes/thomas-pesquet?p=3',
        'info_dict': {
            'id': '86c62790-e481-11e2-9f7b-782bcb6744eb',
            'display_id': 'thomas-pesquet',
            'title': 'Thomas Pesquet',
            'description': 'Astronaute à l\'agence spatiale européenne',
        },
        'playlist_mincount': 100,
    }, {
        'url': 'https://www.radiofrance.fr/personnes/eugenie-bastie',
        'info_dict': {
            'id': '9593050b-0183-4972-a0b5-d8f699079e02',
            'display_id': 'eugenie-bastie',
            'title': 'Eugénie Bastié',
            'description': 'Journaliste et essayiste',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'playlist_mincount': 39,
    }, {
        'url': 'https://www.radiofrance.fr/personnes/lea-salame',
        'only_matching': True,
    }]

    _METADATA_KEY = 'documents'

    def _call_api(self, station, profile_id, cursor):
        url = 'https://www.radiofrance.fr/personnes/' + profile_id + '?p=' + str(cursor)
        webpage = self._download_webpage(url, profile_id, note=f'Downloading {profile_id} page {cursor}')

        resp = dict()

        # On profile pages, the data is stored in a javascript array in the final <script>
        # Each episode is stored as
        # a[0] = { id: ... }; a[1] = [ id: ... ]; on page 2->
        # If a page had a thumbnail, the a variable contains image data,
        # and episode data is stored in b[0]...
        resp['items'] = []
        podcastindex = 0
        nextmatch = True
        while nextmatch:
            nextmatch = self._search_json(r'\w+\[' + str(podcastindex) + r'\]\s*=\s*', webpage, profile_id,
                                          profile_id, transform_source=js_to_json, fatal=False, default=None)
            podcastindex += 1
            if nextmatch is not None:
                resp['items'].append(nextmatch)

        # There is more than one pagination key in the final <script>
        # We should use pick the pagination object which is within a documents object
        pagedata = self._search_json(r'documents\s*:\s*', webpage, profile_id, profile_id,
                                     transform_source=js_to_json)
        lastPage = traverse_obj(pagedata, ('pagination', 'lastPage'))
        hasMorePages = cursor < lastPage
        resp['next'] = cursor + 1 if hasMorePages else None

        resp['metadata'] = self._search_json(r'content:\s*', webpage, profile_id, profile_id,
                                             transform_source=js_to_json)
        # If the image data is stored separately rather than in the main content area
        if resp['metadata']['visual'] and isinstance(resp['metadata']['visual'], str):
            imagedata = dict()
            imagedata['src'] = self._og_search_thumbnail(webpage)
            resp['metadata']['visual'] = imagedata

        return resp


class RadioFranceProgramScheduleIE(RadioFranceBaseIE):
    _VALID_URL = rf'''(?x)
        {RadioFranceBaseIE._VALID_URL_BASE}
        /(?P<station>{RadioFranceBaseIE._STATIONS_RE})
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

    def _generate_playlist_entries(self, webpage_url, api_response):
        for entry in traverse_obj(api_response, ('steps', lambda _, v: v['expression']['path'])):
            yield self.url_result(
                urljoin(webpage_url, f'/{entry["expression"]["path"]}'), ie=FranceCultureIE,
                url_transparent=True, **traverse_obj(entry, {
                    'title': ('expression', 'title'),
                    'thumbnail': ('expression', 'visual', 'src'),
                    'timestamp': ('startTime', {int_or_none}),
                    'series_id': ('concept', 'id'),
                    'series': ('concept', 'title'),
                }))

    def _real_extract(self, url):
        station, date = self._match_valid_url(url).group('station', 'date')
        webpage = self._download_webpage(url, station)
        grid_data = self._extract_data_from_webpage(webpage, station, 'grid')
        upload_date = strftime_or_none(grid_data.get('date'), '%Y%m%d')

        return self.playlist_result(
            self._generate_playlist_entries(url, grid_data),
            join_nonempty(station, 'program', upload_date), upload_date=upload_date)
