import itertools
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
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
    _VALID_URL = r'https?://maison\.radiofrance\.fr/radiovisions/(?P<id>[^?#]+)'
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

    @staticmethod
    def _hydrate_devalue(flat):
        """Inflate a SvelteKit devalue-serialized flat array starting at index 0.

        See https://github.com/Rich-Harris/devalue for the format.
        """
        if not isinstance(flat, list) or not flat:
            return None
        seen = {}

        def hydrate(idx):
            if idx in (-1, -2):
                return None
            if idx == -3:
                return float('nan')
            if idx == -4:
                return float('inf')
            if idx == -5:
                return float('-inf')
            if idx == -6:
                return -0.0
            if idx in seen:
                return seen[idx]
            value = flat[idx]
            if not isinstance(value, (list, dict)):
                seen[idx] = value
                return value
            if isinstance(value, list):
                result = []
                seen[idx] = result
                result.extend(hydrate(v) if isinstance(v, int) else v for v in value)
                return result
            result = {}
            seen[idx] = result
            for k, v in value.items():
                result[k] = hydrate(v) if isinstance(v, int) else v
            return result

        return hydrate(0)

    def _call_data_api(self, path, display_id, query=None, note='Downloading data JSON'):
        """Fetch the SvelteKit /__data.json companion for a page and return the hydrated page content."""
        data = self._download_json(
            f'https://www.radiofrance.fr/{path.strip("/")}/__data.json',
            display_id, note=note, query=query)
        if traverse_obj(data, 'type') == 'redirect':
            raise ExtractorError(
                f'Page redirects to {data.get("location")!r}; retry with that URL',
                expected=True)
        for node in traverse_obj(data, ('nodes', lambda _, v: isinstance(v, dict) and v.get('type') == 'data')):
            content = traverse_obj(self._hydrate_devalue(node.get('data')), ('content', {dict}))
            if content:
                return content
        raise ExtractorError('Page is unavailable or does not exist', expected=True)

    def _extract_data_from_webpage(self, webpage, display_id, key):
        return traverse_obj(self._search_json(
            r'\bconst\s+data\s*=', webpage, key, display_id,
            contains_pattern=r'\[\{(?s:.+)\}\]', transform_source=js_to_json, default=None),
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
                'thumbnail': r're:^https?://www\.radiofrance\.fr/pikapi/images/.+',
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
                'thumbnail': r're:^https?://www\.radiofrance\.fr/pikapi/images/.+',
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
            api_response = self._extract_data_from_webpage(webpage, station_id, 'webRadioData')
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


class RadioFranceTransistorIE(RadioFranceBaseIE):
    IE_NAME = 'radiofrance:transistor'
    _VALID_URL = rf'{RadioFranceBaseIE._VALID_URL_BASE}/transistor/aod/(?P<id>[0-9a-f-]+)'

    _TESTS = [{
        # episode of a "serie" podcast with no individual page
        'url': 'https://www.radiofrance.fr/transistor/aod/fb76501c-09d3-4167-98d7-3f02194d2d18',
        'info_dict': {
            'id': 'fb76501c-09d3-4167-98d7-3f02194d2d18',
            'ext': 'm4a',
            'title': r're:.*Les Malheurs de Sophie.* - .+',
            'series': r're:.*Les Malheurs de Sophie.*',
            'episode': str,
            'thumbnail': r're:^https?://www\.radiofrance\.fr/pikapi/images/.+',
        },
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        data = self._download_json(
            f'https://www.radiofrance.fr/transistor/aod/{audio_id}', audio_id,
            note='Downloading audio metadata')

        formats = []
        for source in traverse_obj(data, ('sources', lambda _, v: v['url'])):
            ext = determine_ext(source['url'])
            formats.append({
                'url': source['url'],
                'format_id': traverse_obj(source, ('preset', 'name', {str})) or ext,
                'ext': ext,
                'acodec': traverse_obj(source, ('preset', 'encoding', {str.lower})),
                'abr': traverse_obj(source, ('preset', 'bitrate', {int_or_none})),
                'vcodec': 'none',
            })

        first_line = traverse_obj(data, ('metadata', 'firstLine', {str}))
        second_line = traverse_obj(data, ('metadata', 'secondLine', {str.strip}))
        cover_id = traverse_obj(data, ('metadata', 'cover', 'id', {str}))

        thumbnail = None
        if cover_id:
            # pikapi requires a size suffix; ?webp=false forces JPEG for embedders
            thumbnail = f'https://www.radiofrance.fr/pikapi/images/{cover_id}/2048?webp=false'

        return {
            'id': audio_id,
            'title': join_nonempty(first_line, second_line, delim=' - ') or audio_id,
            'series': first_line,
            'episode': second_line,
            'thumbnail': thumbnail,
            'formats': formats,
        }


class RadioFrancePlaylistBaseIE(RadioFranceBaseIE):
    """Subclasses must set _METADATA_KEY"""

    def _call_api(self, path, page_num):
        return traverse_obj(
            self._call_data_api(path, path, query={'p': page_num},
                                note=f'Downloading page {page_num}'),
            (self._METADATA_KEY, {dict})) or {}

    @staticmethod
    def _pikapi_thumbnail(visual):
        """Build a usable thumbnail URL from a `visual` object (pikapi requires a size suffix)."""
        src = traverse_obj(visual, ('src', {str}))
        if not src:
            return None
        return f'{src.rstrip("/")}/2048?webp=false'

    def _generate_playlist_entries(self, path, content_response):
        # FranceCultureIE only matches episode URLs ending in -\d{6,}; for any other shape
        # (e.g. legacy slugs, "serie" episodes with no page) we fall back to transistor/aod.
        france_culture_url_re = re.compile(r'-\d{6,}(?:[?#]|$)')
        for page_num in itertools.count(2):
            for entry in traverse_obj(content_response, ('items', lambda _, v: v.get('id'))):
                metadata = traverse_obj(entry, {
                    'title': ('titleProps', 'title', {str.strip}),
                    'description': ('titleProps', 'text', {str.strip}),
                    'duration': ('manifestation', 'duration', {int_or_none}),
                })
                metadata['thumbnail'] = self._pikapi_thumbnail(entry.get('visual'))
                href = traverse_obj(entry, ('titleProps', 'href', {str}, filter))
                if href and france_culture_url_re.search(href):
                    yield self.url_result(
                        urljoin('https://www.radiofrance.fr', href),
                        url_transparent=True, **metadata)
                else:
                    yield self.url_result(
                        f'https://www.radiofrance.fr/transistor/aod/{entry["id"]}',
                        ie=RadioFranceTransistorIE.ie_key(), video_id=entry['id'],
                        url_transparent=True, **metadata)

            if not traverse_obj(content_response, ('next', {str}, filter)):
                break
            content_response = self._call_api(path, page_num)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        path = urllib.parse.urlparse(url).path
        content = self._call_data_api(path, display_id)

        return self.playlist_result(
            self._generate_playlist_entries(path, content.get(self._METADATA_KEY) or {}),
            content.get('id') or display_id,
            display_id=display_id, thumbnail=self._pikapi_thumbnail(content.get('visual')),
            **traverse_obj(content, {
                'title': (('title', 'name'), {str}, any),
                'description': (('standFirst', 'role', 'chapo', 'baseline'), {str.strip}, filter, any),
            }))


class RadioFrancePodcastIE(RadioFrancePlaylistBaseIE):
    _VALID_URL = rf'''(?x)
        {RadioFranceBaseIE._VALID_URL_BASE}
        /(?:{RadioFranceBaseIE._STATIONS_RE})
        /podcasts/(?P<id>[\w-]+)/?(?:[?#]|$)
    '''

    _TESTS = [{
        'url': 'https://www.radiofrance.fr/franceinfo/podcasts/le-billet-sciences',
        'info_dict': {
            'id': 'eaf6ef81-a980-4f1c-a7d1-8a75ecd54b17',
            'display_id': 'le-billet-sciences',
            'title': 'Le billet sciences',
            'description': 'md5:be91a0218154c0c69f18e0d9a2ce4b16',
            'thumbnail': r're:^https?://www\.radiofrance\.fr/pikapi/images/.+',
        },
        'playlist_mincount': 11,
    }, {
        # "serie" podcast: episodes have no individual page, resolved via transistor/aod
        'url': 'https://www.radiofrance.fr/franceculture/podcasts/serie-les-malheurs-de-sophie-une-comedie-musicale-de-sabine-zovighian-et-michael-liot',
        'info_dict': {
            'id': 'a61c5684-b251-4bee-9566-1f8300c66aa9',
            'display_id': 'serie-les-malheurs-de-sophie-une-comedie-musicale-de-sabine-zovighian-et-michael-liot',
            'title': r're:.*Les Malheurs de Sophie.*',
            'thumbnail': r're:^https?://www\.radiofrance\.fr/pikapi/images/.+',
        },
        'playlist_count': 5,
    }, {
        'url': 'https://www.radiofrance.fr/fip/podcasts/certains-l-aiment-fip',
        'info_dict': {
            'id': '143dff38-e956-4a5d-8576-1c0b7242b99e',
            'display_id': 'certains-l-aiment-fip',
            'title': 'Certains l’aiment Fip',
            'thumbnail': r're:^https?://www\.radiofrance\.fr/pikapi/images/.+',
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
        'playlist_mincount': 212,
    }, {
        'url': 'https://www.radiofrance.fr/personnes/eugenie-bastie',
        'info_dict': {
            'id': '9593050b-0183-4972-a0b5-d8f699079e02',
            'display_id': 'eugenie-bastie',
            'title': 'Eugénie Bastié',
            'description': 'Journaliste et essayiste',
            'thumbnail': r're:^https?://www\.radiofrance\.fr/pikapi/images/.+',
        },
        'playlist_mincount': 39,
    }, {
        'url': 'https://www.radiofrance.fr/personnes/lea-salame',
        'only_matching': True,
    }]

    _METADATA_KEY = 'documents'


class RadioFranceProgramScheduleIE(RadioFranceBaseIE):
    _VALID_URL = rf'''(?x)
        {RadioFranceBaseIE._VALID_URL_BASE}
        /(?P<station>{RadioFranceBaseIE._STATIONS_RE})
        /grille-programmes
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
        station = self._match_valid_url(url).group('station')
        webpage = self._download_webpage(url, station)
        grid_data = self._extract_data_from_webpage(webpage, station, 'grid')
        upload_date = strftime_or_none(grid_data.get('date'), '%Y%m%d')

        return self.playlist_result(
            self._generate_playlist_entries(url, grid_data),
            join_nonempty(station, 'program', upload_date), upload_date=upload_date)
