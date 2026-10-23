import itertools
import re
import urllib.parse
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from yt_dlp.utils._utils import InAdvancePagedList, clean_html, str_or_none, url_or_none

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    js_to_json,
    traverse_obj,
    unified_strdate,
)


class RadioCanadaIE(InfoExtractor):
    IE_NAME = 'radiocanada'
    _VALID_URL = r'(?:radiocanada:|https?://ici\.radio-canada\.ca/widgets/mediaconsole/)(?P<app_code>[^:/]+)[:/](?P<id>[0-9]+)'
    _TESTS = [
        {
            'url': 'http://ici.radio-canada.ca/widgets/mediaconsole/medianet/7184272',
            'info_dict': {
                'id': '7184272',
                'ext': 'mp4',
                'title': 'Le parcours du tireur capté sur vidéo',
                'description': 'Images des caméras de surveillance fournies par la GRC montrant le parcours du tireur d\'Ottawa',
                'upload_date': '20141023',
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            # empty Title
            'url': 'http://ici.radio-canada.ca/widgets/mediaconsole/medianet/7754998/',
            'info_dict': {
                'id': '7754998',
                'ext': 'mp4',
                'title': 'letelejournal22h',
                'description': 'INTEGRALE WEB 22H-TJ',
                'upload_date': '20170720',
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            # with protectionType but not actually DRM protected
            'url': 'radiocanada:toutv:140872',
            'info_dict': {
                'id': '140872',
                'title': 'Épisode 1',
                'series': 'District 31',
            },
            'only_matching': True,
        },
    ]
    _GEO_COUNTRIES = ['CA']
    _access_token = None
    _claims = None

    def _call_api(self, path, video_id=None, app_code=None, query=None):
        if not query:
            query = {}
        query.update({
            'client_key': '773aea60-0e80-41bb-9c7f-e6d7c3ad17fb',
            'output': 'json',
        })
        if video_id:
            query.update({
                'appCode': app_code,
                'idMedia': video_id,
            })
        if self._access_token:
            query['access_token'] = self._access_token
        try:
            return self._download_json(
                'https://services.radio-canada.ca/media/' + path, video_id, query=query)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in (401, 422):
                data = self._parse_json(e.cause.response.read().decode(), None)
                error = data.get('error_description') or data['errorMessage']['text']
                raise ExtractorError(error, expected=True)
            raise

    def _extract_info(self, app_code, video_id):
        metas = self._call_api('meta/v1/index.ashx', video_id, app_code)['Metas']

        def get_meta(name):
            for meta in metas:
                if meta.get('name') == name:
                    text = meta.get('text')
                    if text:
                        return text

        # protectionType does not necessarily mean the video is DRM protected (see
        # https://github.com/ytdl-org/youtube-dl/pull/18609).
        if get_meta('protectionType'):
            self.report_warning('This video is probably DRM protected.')

        query = {
            'connectionType': 'hd',
            'deviceType': 'ipad',
            'multibitrate': 'true',
        }
        if self._claims:
            query['claims'] = self._claims
        v_data = self._call_api('validation/v2/', video_id, app_code, query)
        v_url = v_data.get('url')
        if not v_url:
            error = v_data['message']
            if error == "Le contenu sélectionné n'est pas disponible dans votre pays":
                raise self.raise_geo_restricted(error, self._GEO_COUNTRIES)
            if error == 'Le contenu sélectionné est disponible seulement en premium':
                self.raise_login_required(error)
            raise ExtractorError(
                f'{self.IE_NAME} said: {error}', expected=True)
        formats = self._extract_m3u8_formats(v_url, video_id, 'mp4')

        subtitles = {}
        closed_caption_url = get_meta('closedCaption') or get_meta('closedCaptionHTML5')
        if closed_caption_url:
            subtitles['fr'] = [{
                'url': closed_caption_url,
                'ext': determine_ext(closed_caption_url, 'vtt'),
            }]

        return {
            'id': video_id,
            'title': get_meta('Title') or get_meta('AV-nomEmission'),
            'description': get_meta('Description') or get_meta('ShortDescription'),
            'thumbnail': get_meta('imageHR') or get_meta('imageMR') or get_meta('imageBR'),
            'duration': int_or_none(get_meta('length')),
            'series': get_meta('Emission'),
            'season_number': int_or_none(get_meta('SrcSaison')),
            'episode_number': int_or_none(get_meta('SrcEpisode')),
            'upload_date': unified_strdate(get_meta('Date')),
            'subtitles': subtitles,
            'formats': formats,
        }

    def _real_extract(self, url):
        return self._extract_info(*self._match_valid_url(url).groups())


class RadioCanadaAudioVideoIE(InfoExtractor):
    IE_NAME = 'radiocanada:audiovideo'
    _VALID_URL = r'https?://ici\.radio-canada\.ca/([^/]+/)*media-(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://ici.radio-canada.ca/audio-video/media-7527184/barack-obama-au-vietnam',
        'info_dict': {
            'id': '7527184',
            'ext': 'mp4',
            'title': 'Barack Obama au Vietnam',
            'description': 'Les États-Unis lèvent l\'embargo sur la vente d\'armes qui datait de la guerre du Vietnam',
            'upload_date': '20160523',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://ici.radio-canada.ca/info/videos/media-7527184/barack-obama-au-vietnam',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self.url_result(f'radiocanada:medianet:{self._match_id(url)}')


def find_nested_json_property(obj: dict, key: str):
    """Recursively search a JSON dictionary for a key and return its value or None."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = find_nested_json_property(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_nested_json_property(item, key)
            if found is not None:
                return found
    return None


def iter_use_strict_slices(js: str) -> Iterator[str]:
    """Iterate over slices of JavaScript code between consecutive "use strict"; markers."""
    marker_re = re.compile(r'"use strict";')
    starts = [m.start() for m in marker_re.finditer(js)]

    if not starts:
        return

    # Between consecutive "use strict"; markers
    for a, b in itertools.pairwise(starts):
        yield js[a:b]

    # From the last marker to end of the string
    yield js[starts[-1]:]


rc_string_sanitization_replacements = {
    '’': "'",
    '–': '-',
}


def sanitize_ohdio_string(s: str) -> str:
    """Replace certain characters used by Ohdio to avoid issues with filenames and metadata."""
    if s is None:
        return s

    s = s.strip()
    for old, new in rc_string_sanitization_replacements.items():
        s = s.replace(old, new)
    return s


class RadioCanadaOhdioBaseIE(InfoExtractor):
    _OHDIO_SECTION = None
    IE_NAME = 'radiocanada:ohdio'
    _BASE_URL = 'https://ici.radio-canada.ca/ohdio'
    _BASE_URL_RE = r'https?://ici\.radio-canada\.ca/ohdio/'
    _GEO_COUNTRIES = ['CA']
    _THUMBNAIL_SIZE = 500

    _url_mobj: re.Match[str] | None = None
    _video_id: str | None = None
    _slug: str | None = None
    _page_info: 'RadioCanadaOhdioBaseIE.OhdioPageInfo | None' = None
    _services_url: str | None = None
    _media_info_path: str | None = None

    @staticmethod
    def _make_ohdio_url_re(section: str) -> str:
        return RadioCanadaOhdioBaseIE._BASE_URL_RE + section + r'/(?P<id>[0-9]+)/(?P<slug>[\w\-]+)'

    @dataclass
    class OhdioPageInfo:
        url: str
        url_path: str
        webpage: str
        react_state: dict
        page_data: dict

    @property
    def _url(self) -> str:
        return self._url_mobj.string

    def _init_extract(self, url: str):
        mobj = self._match_valid_url(url)
        self._url_mobj = mobj
        self._video_id = mobj.group('id')
        self._slug = mobj.group('slug')

        self._page_info = self._get_ohdio_page_info(url)
        self._read_media_config()

    def _get_ohdio_page_info(self, url: str) -> 'RadioCanadaOhdioBaseIE.OhdioPageInfo':
        webpage = self._download_webpage(url, self._video_id, 'Ohdio page')

        react_state = self._search_json(r'window\._rcState_\s*=', webpage, 'Ohdio react state', self._video_id)
        url_path = urllib.parse.urlsplit(url).path
        page_state = find_nested_json_property(react_state, url_path)
        if not isinstance(page_state, dict):
            raise ExtractorError('Unable to extract Ohdio page data')
        page_data = page_state['data']

        return self.OhdioPageInfo(url, url_path, webpage, react_state, page_data)

    def _read_media_config(self):
        player_url = find_nested_json_property(self._page_info.react_state, 'apiRouting')['player']['baseUrl']
        player_js = self._download_webpage(player_url, self._video_id, 'Ohdio player')

        # Another interesting object is "clientKey", which supplies the value used in the
        # Authorization header of the media info request, but it doesn't seem to be necessary
        # (for now?). Media requests in the web app also include an "X-Requested-With" header,
        # but it also doesn't seem to be necessary (again, for now?).
        # e.g. 'Authorization Client-Key c0a5fb4e-ea30-43f5-a340-c145c4f05ea5' and
        # 'X-Requested-With: HttpClient (Windows 10) Player Web/2.33.0 (production)'
        player_config = self._search_json_values_in_use_strict_slices(player_js, ['servicesUrl', 'validationMediaPath'])
        if player_config is None:
            raise ExtractorError('Unable to extract player config')

        self._services_url = player_config['servicesUrl']['production']
        self._media_info_path = player_config['validationMediaPath']

    def _get_picture_url(self, url_pattern: str | None) -> str:
        if not url_pattern:
            return ''
        return url_pattern.replace('{width}', str(self._THUMBNAIL_SIZE)).replace('{ratio}', '1x1')

    def _extract_media_item_formats_and_subtitles(self, media_id: str):
        m3u8_url = self._get_m3u8_url(media_id)
        return self._extract_m3u8_formats_and_subtitles(m3u8_url, self._video_id)

    def _get_m3u8_url(self, media_id: str) -> str:
        # Example request from the web app:
        # https://services.radio-canada.ca/media/validation/v2/?appCode=medianet&connectionType=hd&deviceType=ipad&idMedia=10676528&multibitrate=true&output=json&tech=hls&manifestVersion=2
        # Authorization Client-Key c0a5fb4e-ea30-43f5-a340-c145c4f05ea5
        # X-Requested-With: HttpClient (Windows 10) Player Web/2.33.0 (production)
        url = f'{self._services_url}{self._media_info_path}?appCode=medianet&connectionType=hd&deviceType=ipad&idMedia={media_id}&multibitrate=true&output=json&tech=hls&manifestVersion=2'
        media_info = self._download_json(url, self._video_id, f'Ohdio media info ({media_id})')
        return media_info.get('url')

    def _search_json_values_in_use_strict_slices(self, js: str, key_names: Sequence[str]) -> dict[str, dict | str] | None:
        """
        Search for JSON values of *all* requested keys in a single slice of JavaScript code between
        consecutive "use strict"; markers. That's the pattern of bundled and minified JavaScript
        code, where each slice is a separate module.
        Supports object and string value types.
        """
        for js_slice in iter_use_strict_slices(js):
            result = {}
            for key in key_names:
                # E.g. "servicesUrl": {"production": "https://services.radio-canada.ca/media/validation/v2/"}
                # E.g. "apiKey": "c0a5fb4e-ea30-43f5-a340-c145c4f05ea5"
                mobj = re.search(r'["\']?' + key + r'["\']?\s*:\s*(.*)', js_slice)
                if mobj is None:
                    break

                value_slice = mobj.group(1)

                # Object value type
                json_value = self._search_json('', value_slice, key, self._video_id, default=None, transform_source=js_to_json)

                if json_value is None:
                    # String literal type
                    if value_slice[0] in ('"', "'"):
                        separator = value_slice[0]
                        mobj = re.search(separator + r'((?:[^' + separator + r']|(?<=\\)' + separator + r')+)' + separator, value_slice)
                        json_value = mobj.group(1) if mobj else None

                if json_value is None:
                    break

                result[key] = json_value

            if len(result) == len(key_names):
                return result

        return None


class RadioCanadaOhdioLivresAudioIE(RadioCanadaOhdioBaseIE):
    _OHDIO_SECTION = 'livres-audio'
    IE_NAME = RadioCanadaOhdioBaseIE.IE_NAME + f':{_OHDIO_SECTION}'
    _VALID_URL = RadioCanadaOhdioBaseIE._make_ohdio_url_re(_OHDIO_SECTION)

    @staticmethod
    def _make_playlist_test(test_base: dict, chapter_base: dict, chapter_titles: list[str]) -> dict:
        info = test_base['info_dict']
        entries = [{'info_dict': {
            **chapter_base,
            'id': f"{info['id']}-{i + 1}",
            'display_id': f"{chapter_base['display_id']}-{i + 1}",
            'title': f"{info['title']} - {chapter_title}" if chapter_title is not None else info['title'],
            'chapter': chapter_title,
            'chapter_number': i + 1,
            'track_number': i + 1,
        }} for i, chapter_title in enumerate(chapter_titles)]

        return {
            **test_base,
            'playlist': entries,
        }

    _TESTS = [{
        # Single file audiobook
        'url': 'https://ici.radio-canada.ca/ohdio/livres-audio/106115/leon-le-raton-camping-guimauves-et-petits-frissons',
        'info_dict': {
            'ext': 'm4a',
            'id': '106115',
            'title': 'Léon le raton : Camping, guimauves et petits frissons',
            'creators': ['Lucie Papineau'],
            'description': r're:Léon le raton est en vacances au camping de la rivière Framboise.* | Publié en 2021 | Québec Amérique | 32 pages | Tout public',
            'display_id': 'leon-le-raton-camping-guimauves-et-petits-frissons',
            'thumbnail': fr'https://images.radio-canada.ca/q_auto,w_{RadioCanadaOhdioBaseIE._THUMBNAIL_SIZE}/v1/audio/generateur-images/1x1/leon-le-raton-camping-guimauves-et-petits-frissons.jpg',
        },
    }, _make_playlist_test({
        # Multiple file audiobook
        'url': 'https://ici.radio-canada.ca/ohdio/livres-audio/106116/mister-big-ou-la-glorification-des-amours-toxiques',
        'info_dict': {
            'id': '106116',
            'title': 'Mister Big ou la glorification des amours toxiques',
        },
    }, {
        'ext': 'm4a',
        'display_id': 'mister-big-ou-la-glorification-des-amours-toxiques',
        'creators': ['India Desjardins'],
        'description': r're:La fiction pourrait-elle influencer notre perspective du monde.* | Publié en 2021 | Québec Amérique | 192 pages | Tout public',
        'thumbnail': fr'https://images.radio-canada.ca/q_auto,w_{RadioCanadaOhdioBaseIE._THUMBNAIL_SIZE}/v1/audio/livre-audio/1x1/ohdio-mister-big-amours-toxiques-desjardins.jpg',
    }, [
        'Partie 1 - Prologue et chapitres 1 à 3',
        'Partie 2 - Chapitres 4 à 6',
        'Partie 3 - Chapitres 7 à 9',
        'Partie 4 - Chapitres 10 à 13 et remerciements',
    ])]

    def _get_base_info(self):
        info = self._search_json_ld(self._page_info.webpage, self._video_id, expected_type='Audiobook', default={})
        title = sanitize_ohdio_string(info.get('title'))
        description = sanitize_ohdio_string(info.get('description'))
        author = sanitize_ohdio_string(info.get('uploader'))

        picture_url_pattern = traverse_obj(self._page_info.page_data, ('header', 'picture', 'pattern'), expected_type=url_or_none)
        picture_url = self._get_picture_url(picture_url_pattern)

        publisher_information = clean_html(traverse_obj(self._page_info.page_data, ('content', 'about', 'publisherInformation')))

        if description is None:
            description = publisher_information
        elif publisher_information is not None:
            description = f'{description} | {publisher_information}'

        return {
            'display_id': self._slug,
            'title': title,
            'creators': [author] if author else None,
            'description': description,
            'thumbnail': picture_url,
        }

    def _real_extract(self, url: str):
        self._init_extract(url)

        items = traverse_obj(self._page_info.page_data, ('content', 'contentDetail', 'items'), expected_type=list)
        if items is None or len(items) == 0:
            raise ExtractorError('Unable to extract items from page data')

        base_info_dict = self._get_base_info()

        if len(items) == 1:
            media_id = find_nested_json_property(items[0], 'mediaId')
            formats, subtitles = self._extract_media_item_formats_and_subtitles(media_id)
            return {
                **base_info_dict,
                'id': self._video_id,
                'formats': formats,
                'subtitles': subtitles,
            }

        entries = []
        for i, item in enumerate(items):
            track_number = i + 1
            display_id = f"{base_info_dict['display_id']}-{track_number}"
            if item.get('title'):
                chapter_title = sanitize_ohdio_string(item.get['title'])
                if (base_info_dict.get('title')):
                    title = f"{base_info_dict['title']} - {chapter_title}"
                else:
                    title = chapter_title
            else:
                chapter_title = None
                title = base_info_dict.get('title')

            media_id = find_nested_json_property(item, 'mediaId')
            formats, subtitles = self._extract_media_item_formats_and_subtitles(media_id)

            entries.append({
                **base_info_dict,
                'id': f'{self._video_id}-{track_number}',
                'display_id': display_id,
                'title': title,
                'chapter': chapter_title,
                'chapter_number': track_number,
                'track_number': track_number,
                'formats': formats,
                'subtitles': subtitles,
            })

        return self.playlist_result(entries, self._video_id, base_info_dict['title'], multi_video=True)


class RadioCanadaOhdioBaladosIE(RadioCanadaOhdioBaseIE):
    _OHDIO_SECTION = 'balados'
    IE_NAME = RadioCanadaOhdioBaseIE.IE_NAME + f':{_OHDIO_SECTION}'
    _VALID_URL = RadioCanadaOhdioBaseIE._make_ohdio_url_re(_OHDIO_SECTION) + r'(?:/(?P<episode_id>[0-9]+)/(?P<episode_slug>[\w\-]+))?'
    _TESTS = [{
        # Single page podcast series
        'url': 'https://ici.radio-canada.ca/ohdio/balados/10626/comptines-alfa-rococo-florence-k',
        'info_dict': {
            'id': '10626',
            'title': 'comptines-alfa-rococo-florence-k',
        },
        'playlist_count': 10,
    }, {
        # Single podcast episode
        'url': 'https://ici.radio-canada.ca/ohdio/balados/10626/comptines-alfa-rococo-florence-k/689174/crocodiles-alfa-rococo-famille-enfants',
        'info_dict': {
            'id': '10626',
            'title': 'comptines-alfa-rococo-florence-k',
        },
        'playlist': [{
            'info_dict': {
                'ext': 'm4a',
                'id': '689174',
                'title': 'Comptines - Ah! Les crocodiles interprété par Alfa Rococo',
                'display_id': 'crocodiles-alfa-rococo-famille-enfants',
                'thumbnail': fr'https://images.radio-canada.ca/q_auto,w_{RadioCanadaOhdioBaseIE._THUMBNAIL_SIZE}/v1/audio/balado/1x1/comptines-balado-ohdio-moteur.jpg',
            },
        }],
    }, {
        # Paginated podcast series, explicit page number
        'url': 'https://ici.radio-canada.ca/ohdio/balados/6108/ca-sexplique-balado-info-alexis-de-lancer?pageNumber=2',
        'info_dict': {
            'id': '6108',
            'title': 'ca-sexplique-balado-info-alexis-de-lancer',
        },
        'playlist_mincount': 20,
    }]

    def _get_podcast_episode_entry(self, page_info: RadioCanadaOhdioBaseIE.OhdioPageInfo) -> dict:
        slug = re.match(self._VALID_URL, page_info.url).group('episode_slug')

        header = page_info.page_data['header']
        episode_id = traverse_obj(header, ('globalId', 'id'), expected_type=str)
        title = sanitize_ohdio_string(header.get('title'))
        description = sanitize_ohdio_string(clean_html(header.get('summary')))

        picture_url_pattern = traverse_obj(header, ('picture', 'pattern'), expected_type=url_or_none)
        picture_url = self._get_picture_url(picture_url_pattern)

        episode_credits = sanitize_ohdio_string(traverse_obj(page_info.page_data, ('content', 'credits'), expected_type=str_or_none))

        media_id = traverse_obj(header, ('playlistItemId', 'mediaId'), expected_type=str)
        formats, subtitles = self._extract_media_item_formats_and_subtitles(media_id)

        return {
            'id': episode_id,
            'display_id': slug,
            'title': title,
            'description': description,
            'thumbnail': picture_url,
            'creators': [episode_credits] if episode_credits else None,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _get_podcast_series_page_entries(self, page_index: int, page_info: RadioCanadaOhdioBaseIE.OhdioPageInfo) -> Iterator[dict]:
        episodes = traverse_obj(page_info.page_data, ('episodes'), expected_type=list)
        if episodes is None or len(episodes) == 0:
            raise ExtractorError(f'Unable to extract episodes from page {page_index + 1} data')

        for episode in episodes:
            episode_url = self._BASE_URL + episode['url']
            page_info = self._get_ohdio_page_info(episode_url)
            yield self._get_podcast_episode_entry(page_info)

    def _fetch_podcast_series_page(self, page_index: int) -> Iterator[dict]:
        if page_index == 0:
            page_info = self._page_info
        else:
            page_url = f'{self._url}?pageNumber={page_index + 1}'
            page_info = self._get_ohdio_page_info(page_url)

        yield from self._get_podcast_series_page_entries(page_index, page_info)

    def _real_extract(self, url: str):
        self._init_extract(url)
        self._episode_id = self._url_mobj.group('episode_id')
        self._episode_slug = self._url_mobj.group('episode_slug')

        if (self._episode_id is None != self._episode_slug is None):
            raise ExtractorError('Both episode_id and episode_slug must be present or absent in the URL')

        if self._episode_id is not None:
            entries = [self._get_podcast_episode_entry(self._page_info)]
        else:
            # If there's a page number, we assume the user is requesting a specific page's content, not all pages
            explicit_page_number = int_or_none(urllib.parse.parse_qs(urllib.parse.urlsplit(self._url).query).get('pageNumber', [None])[0])
            if explicit_page_number is not None:
                entries = list(self._get_podcast_series_page_entries(explicit_page_number, self._page_info))
            else:
                pagination_info = self._page_info.page_data['pagination']
                page_size = pagination_info['pageSize']
                total_count = pagination_info['totalCount']
                page_count = (total_count + page_size - 1) // page_size
                entries = InAdvancePagedList(self._fetch_podcast_series_page, page_count, page_size)

        return self.playlist_result(entries, self._video_id, self._slug)
