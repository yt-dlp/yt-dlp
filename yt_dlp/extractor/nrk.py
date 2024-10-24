import itertools
import json
import random
import re

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    parse_duration,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    url_or_none,
    urljoin,
)


class NRKBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['NO']
    _CDN_REPL_REGEX = r'''(?x)://
        (?:
            nrkod\d{1,2}-httpcache0-47115-cacheod0\.dna\.ip-only\.net/47115-cacheod0|
            nrk-od-no\.telenorcdn\.net|
            minicdn-od\.nrk\.no/od/nrkhd-osl-rr\.netwerk\.no/no
        )/'''
    _NETRC_MACHINE = 'nrk'
    _LOGIN_URL = 'https://innlogging.nrk.no/logginn'
    _AUTH_TOKEN = ''
    _API_CALL_HEADERS = {'Accept': 'application/json;device=player-core'}

    def _extract_nrk_formats_and_subtitles(self, asset_url, video_id):

        if re.match(r'https?://[^/]+\.akamaihd\.net/i/', asset_url):
            return self._extract_akamai_formats(asset_url, video_id)
        asset_url = re.sub(r'(?:bw_(?:low|high)=\d+|no_audio_only|adap=.+?\b)&?', '', asset_url)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            asset_url, video_id, 'mp4', 'm3u8_native', fatal=False)
        if not formats and re.search(self._CDN_REPL_REGEX, asset_url):
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                re.sub(self._CDN_REPL_REGEX, '://nrk-od-%02d.akamaized.net/no/' % random.randint(0, 99), asset_url),
                video_id, 'mp4', 'm3u8_native', fatal=False)
        return formats, subtitles

    def _raise_error(self, data):
        MESSAGES = {
            'ProgramRightsAreNotReady': 'Du kan dessverre ikke se eller høre programmet',
            'ProgramRightsHasExpired': 'Programmet har gått ut',
            'NoProgramRights': 'Ikke tilgjengelig',
            'ProgramIsGeoBlocked': 'NRK har ikke rettigheter til å vise dette programmet utenfor Norge',
        }
        message_type = data.get('messageType', '')
        # Can be ProgramIsGeoBlocked or ChannelIsGeoBlocked*
        if 'IsGeoBlocked' in message_type or traverse_obj(data, ('usageRights', 'isGeoBlocked')) is True:
            self.raise_geo_restricted(
                msg=MESSAGES.get('ProgramIsGeoBlocked'),
                countries=self._GEO_COUNTRIES)
        message = data.get('endUserMessage') or MESSAGES.get(message_type, message_type)
        raise ExtractorError(f'{self.IE_NAME} said: {message}', expected=True)

    def _call_api(self, path, video_id, item=None, note=None, fatal=True, query=None):
        return self._download_json(
            urljoin('https://psapi.nrk.no/', path),
            video_id, note or f'Downloading {item} JSON',
            fatal=fatal, query=query, headers=self._API_CALL_HEADERS)


class NRKIE(NRKBaseIE):
    _VALID_URL = r'''(?x)
                        (?:
                            nrk:|
                            https?://
                                (?:
                                    (?:www\.)?nrk\.no/video/(?:PS\*|[^_]+_)|
                                    v8[-.]psapi\.nrk\.no/mediaelement/
                                )
                            )
                            (?P<id>[^?\#&]+)
                        '''
    _TESTS = [{
        # video
        'url': 'http://www.nrk.no/video/PS*150533',
        'md5': '2b88a652ad2e275591e61cf550887eec',
        'info_dict': {
            'id': '150533',
            'ext': 'mp4',
            'title': 'Dompap og andre fugler i Piip-Show',
            'description': 'md5:d9261ba34c43b61c812cb6b0269a5c8f',
            'duration': 262,
            'timestamp': 1395751833,
            'upload_date': '20140325',
            'thumbnail': 'https://gfx.nrk.no/0mZgeckEzRU6qTWrbQHD2QcyralHrYB08wBvh-K-AtAQ',
            'alt_title': 'md5:d9261ba34c43b61c812cb6b0269a5c8f',
        },
    }, {
        # audio
        'url': 'http://www.nrk.no/video/PS*154915',
        # MD5 is unstable
        'info_dict': {
            'id': '154915',
            'ext': 'mp4',
            'title': 'Slik høres internett ut når du er blind',
            'description': 'md5:a621f5cc1bd75c8d5104cb048c6b8568',
            'duration': 20,
            'alt_title': 'Cathrine Lie Wathne er blind, og bruker hurtigtaster for å navigere seg rundt på ulike nettsider.',
            'upload_date': '20140425',
            'timestamp': 1398429565,
            'thumbnail': 'https://gfx.nrk.no/urxQMSXF-WnbfjBH5ke2igLGyN27EdJVWZ6FOsEAclhA',
        },
    }, {
        'url': 'nrk:ecc1b952-96dc-4a98-81b9-5296dc7a98d9',
        'only_matching': True,
    }, {
        'url': 'nrk:clip/7707d5a3-ebe7-434a-87d5-a3ebe7a34a70',
        'only_matching': True,
    }, {
        'url': 'https://v8-psapi.nrk.no/mediaelement/ecc1b952-96dc-4a98-81b9-5296dc7a98d9',
        'only_matching': True,
    }, {
        'url': 'https://www.nrk.no/video/dompap-og-andre-fugler-i-piip-show_150533',
        'only_matching': True,
    }, {
        'url': 'https://www.nrk.no/video/humor/kommentatorboksen-reiser-til-sjos_d1fda11f-a4ad-437a-a374-0398bc84e999',
        'only_matching': True,
    }, {
        # podcast
        'url': 'nrk:l_96f4f1b0-de54-4e6a-b4f1-b0de54fe6af8',
        'only_matching': True,
    }, {
        'url': 'nrk:podcast/l_96f4f1b0-de54-4e6a-b4f1-b0de54fe6af8',
        'only_matching': True,
    }, {
        # clip
        'url': 'nrk:150533',
        'only_matching': True,
    }, {
        'url': 'nrk:clip/150533',
        'only_matching': True,
    }, {
        # program
        'url': 'nrk:MDDP12000117',
        'only_matching': True,
    }, {
        'url': 'nrk:program/ENRK10100318',
        'only_matching': True,
    }, {
        # direkte
        'url': 'nrk:nrk1',
        'only_matching': True,
    }, {
        'url': 'nrk:channel/nrk1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).split('/')[-1]

        # known values for preferredCdn: akamai, iponly, minicdn and telenor
        manifest = self._call_api(f'playback/manifest/{video_id}', video_id, 'manifest', query={'preferredCdn': 'akamai'})

        video_id = manifest.get('id') or video_id

        if manifest.get('playability') == 'nonPlayable':
            self._raise_error(manifest['nonPlayable'])

        playable = manifest['playable']

        formats = []
        subtitles = {}
        has_drm = False
        for asset in traverse_obj(playable, ('assets', ..., {dict})):
            encryption_scheme = asset.get('encryptionScheme')
            if encryption_scheme not in (None, 'none', 'statickey'):
                self.report_warning(f'Skipping asset with unsupported encryption scheme "{encryption_scheme}"')
                has_drm = True
                continue
            format_url = url_or_none(asset.get('url'))
            if not format_url:
                continue
            asset_format = (asset.get('format') or '').lower()
            if asset_format == 'hls' or determine_ext(format_url) == 'm3u8':
                fmts, subs = self._extract_nrk_formats_and_subtitles(format_url, video_id)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif asset_format == 'mp3':
                formats.append({
                    'url': format_url,
                    'format_id': asset_format,
                    'vcodec': 'none',
                })

        if not formats and has_drm:
            self.report_drm(video_id)

        data = self._call_api(traverse_obj(manifest, ('_links', 'metadata', 'href', {str})), video_id, 'metadata')

        preplay = data.get('preplay')
        titles = preplay.get('titles')
        title = titles.get('title')
        alt_title = titles.get('subtitle')

        description = preplay.get('description')
        # Use m3u8 vod dueration for NRKSkoleIE because of incorrect duration in metadata
        duration = parse_duration(playable.get('duration')) or parse_duration(data.get('duration')) or self._extract_m3u8_vod_duration(formats[0]['url'], video_id)

        thumbnails = []
        for image in traverse_obj(preplay, ('poster', 'images', {list})) or []:
            if not isinstance(image, dict):
                continue
            image_url = url_or_none(image.get('url'))
            if not image_url:
                continue
            thumbnails.append({
                'url': image_url,
                'width': int_or_none(image.get('pixelWidth')),
                'height': int_or_none(image.get('pixelHeight')),
            })

        for sub in traverse_obj(playable, ('subtitles', {list})) or []:
            if not isinstance(sub, dict):
                continue
            sub_url = url_or_none(sub.get('webVtt'))
            if not sub_url:
                continue

            sub_key = str_or_none(sub.get('language')) or 'nb'
            sub_type = str_or_none(sub.get('type'))
            if sub_type:
                sub_key += f'-{sub_type}'
            subtitles.setdefault(sub_key, []).append({
                'url': sub_url,
            })

        chapters = []
        if data.get('skipDialogInfo'):
            chapters = [item for item in [{
                'start_time': float_or_none(traverse_obj(data, ('skipDialogInfo', 'startIntroInSeconds'))),
                'end_time': float_or_none(traverse_obj(data, ('skipDialogInfo', 'endIntroInSeconds'))),
                'title': 'Intro',
            }, {
                'start_time': float_or_none(traverse_obj(data, ('skipDialogInfo', 'startCreditsInSeconds'))),
                'end_time': duration,
                'title': 'Outro',
            }] if item['start_time'] != item['end_time']]
        if preplay.get('indexPoints'):
            seconds_or_none = lambda x: float_or_none(parse_duration(x))
            chapters += traverse_obj(preplay, ('indexPoints', ..., {
                'start_time': ('startPoint', {seconds_or_none}),
                'end_time': ('endPoint', {seconds_or_none}),
                'title': ('title', {lambda x: x}),
            }))
        chapters = sorted(chapters, key=lambda x: x['start_time']) if chapters else None
        legal_age = traverse_obj(data, ('legalAge', 'body', 'rating', 'code'))
        # https://en.wikipedia.org/wiki/Norwegian_Media_Authority
        age_limit = None
        if legal_age:
            if legal_age == 'A':
                age_limit = 0
            elif legal_age.isdigit():
                age_limit = int_or_none(legal_age)

        is_series = traverse_obj(data, ('_links', 'series', 'name')) == 'series'

        info = {
            'id': video_id,
            'title': title,
            'alt_title': alt_title,
            'description': description,
            'duration': duration,
            'thumbnails': thumbnails,
            'age_limit': age_limit,
            'formats': formats,
            'subtitles': subtitles,
            'chapters': chapters,
            'timestamp': parse_iso8601(traverse_obj(data, ('availability', 'onDemand', 'from'))),
        }
        if is_series:
            series = season_id = season_number = episode = episode_number = None

            programs = self._call_api(
                f'programs/{video_id}', video_id, 'programs', fatal=False)
            matched_dates = [
                int(match.group()) // 1000
                for date in [
                    traverse_obj(programs, ('firstTimeTransmitted', 'publicationDate')),
                    traverse_obj(programs, ('usageRights', 'availableFrom')),
                ] if date for match in [re.search(r'\d+', date)] if match
            ]
            if matched_dates:
                info.update({'timestamp': min(info['timestamp'], *matched_dates)})
            if programs and isinstance(programs, dict):
                series = str_or_none(programs.get('seriesTitle'))
                season_id = str_or_none(programs.get('seasonId'))
                season_number = int_or_none(programs.get('seasonNumber'))
                episode = str_or_none(programs.get('episodeTitle'))
                episode_number = int_or_none(programs.get('episodeNumber'))
            if not series:
                series = title
            if alt_title:
                title += f' - {alt_title}'
            if not season_number:
                season_number = int_or_none(self._search_regex(
                    r'Sesong\s+(\d+)', description or '', 'season number',
                    default=None))
            if not episode:
                episode = alt_title if is_series else None
            if not episode_number:
                episode_number = int_or_none(self._search_regex(
                    r'^(\d+)\.', episode or '', 'episode number',
                    default=None))
            if not episode_number:
                episode_number = int_or_none(self._search_regex(
                    r'\((\d+)\s*:\s*\d+\)', description or '',
                    'episode number', default=None))
            info.update({
                'title': title,
                'series': series,
                'season_id': season_id,
                'season_number': season_number,
                'episode': episode,
                'episode_number': episode_number,
            })

        return info

    def _perform_login(self, username, password):
        try:
            self._download_json(
                self._LOGIN_URL, None, headers={'Content-Type': 'application/json; charset=UTF-8', 'accept': 'application/json; charset=utf-8'},
                data=json.dumps({
                    'clientId': '',
                    'hashedPassword': {'current': {
                        'hash': password,
                        'recipe': {
                            'algorithm': 'cleartext',
                            'salt': '',
                        },
                    },
                    },
                    'password': password,
                    'username': username,
                }).encode())

            self._download_webpage('https://tv.nrk.no/auth/web/login/opsession', None)
            response = self._download_json('https://tv.nrk.no/auth/session/tokenforsub/_', None)
            self._AUTH_TOKEN = traverse_obj(response, ('session', 'accessToken'))
            self._API_CALL_HEADERS['authorization'] = f'Bearer {self._AUTH_TOKEN}'
        except ExtractorError as e:
            message = None
            if isinstance(e.cause, HTTPError) and e.cause.status in (401, 400):
                resp = self._parse_json(
                    e.cause.response.read().decode(), None, fatal=False) or {}
                message = next((error['message'] for error in resp['errors'] if error['field'] == 'Password'), None)
            self.report_warning(message or 'Unable to log in')


class NRKTVIE(NRKBaseIE):
    IE_DESC = 'NRK TV and NRK Radio'
    _EPISODE_RE = r'(?P<id>[a-zA-Z]{4}\d{8})'
    _VALID_URL = rf'https?://(?:tv|radio)\.nrk(?:super)?\.no/(?:[^/]+/)*{_EPISODE_RE}'
    _TESTS = [{
        'url': 'https://tv.nrk.no/program/MDDP12000117',
        'md5': 'c4a5960f1b00b40d47db65c1064e0ab1',
        'info_dict': {
            'id': 'MDDP12000117',
            'ext': 'mp4',
            'title': 'Alarm Trolltunga',
            'description': 'md5:46923a6e6510eefcce23d5ef2a58f2ce',
            'duration': 2223.44,
            'age_limit': 6,
            'subtitles': {
                'nb-nor': [{
                    'ext': 'vtt',
                }],
                'nb-ttv': [{
                    'ext': 'vtt',
                }],
            },
            'upload_date': '20170627',
            'chapters': [{'start_time': 0, 'end_time': 2213.0, 'title': '<Untitled Chapter 1>'}, {'start_time': 2213.0, 'end_time': 2223.44, 'title': 'Outro'}],
            'timestamp': 1498591822,
            'thumbnail': 'https://gfx.nrk.no/myRSc4vuFlahB60P3n6swwRTQUZI1LqJZl9B7icZFgzA',
            'alt_title': 'md5:46923a6e6510eefcce23d5ef2a58f2ce',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://tv.nrk.no/serie/20-spoersmaal-tv/MUHH48000314/23-05-2014',
        'md5': '8d40dab61cea8ab0114e090b029a0565',
        'info_dict': {
            'id': 'MUHH48000314',
            'ext': 'mp4',
            'title': '20 spørsmål - 23. mai 2014',
            'alt_title': '23. mai 2014',
            'description': 'md5:bdea103bc35494c143c6a9acdd84887a',
            'duration': 1741,
            'age_limit': 0,
            'series': '20 spørsmål',
            'episode': '23. mai 2014',
            'upload_date': '20140523',
            'thumbnail': 'https://gfx.nrk.no/u7uCe79SEfPVGRAGVp2_uAZnNc4mfz_kjXg6Bgek8lMQ',
            'season_id': '126936',
            'season_number': 2014,
            'season': 'Season 2014',
            'chapters': [
                {'start_time': 0.0, 'end_time': 39.0, 'title': 'Intro'},
                {'start_time': 0.0, 'title': 'Velkommen', 'end_time': 152.32},
                {'start_time': 152.32, 'title': 'Tannpirker', 'end_time': 304.76},
                {'start_time': 304.76, 'title': 'Orgelbrus', 'end_time': 513.48},
                {'start_time': 513.48, 'title': 'G-streng', 'end_time': 712.96},
                {'start_time': 712.96, 'title': 'Medalje', 'end_time': 837.76},
                {'start_time': 837.76, 'title': 'Globus', 'end_time': 1124.48},
                {'start_time': 1124.48, 'title': 'Primstav', 'end_time': 1417.4},
                {'start_time': 1417.4, 'title': 'Fyr', 'end_time': 1721.0},
                {'start_time': 1721.0, 'end_time': 1741.0, 'title': 'Outro'},
            ],
            'episode_number': 3,
            'timestamp': 1400871900,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://tv.nrk.no/program/mdfp15000514',
        'info_dict': {
            'id': 'MDFP15000514',
            'ext': 'mp4',
            'title': 'Kunnskapskanalen - Grunnlovsjubiléet - Stor ståhei for ingenting',
            'description': 'md5:89290c5ccde1b3a24bb8050ab67fe1db',
            'duration': 4605.08,
            'series': 'Kunnskapskanalen',
            'episode': 'Grunnlovsjubiléet - Stor ståhei for ingenting',
            'age_limit': 0,
            'upload_date': '20140524',
            'episode_number': 17,
            'chapters': [
                {'start_time': 0, 'end_time': 4595.0, 'title': '<Untitled Chapter 1>'},
                {'start_time': 4595.0, 'end_time': 4605.08, 'title': 'Outro'},
            ],
            'season': 'Season 2014',
            'timestamp': 1400937600,
            'thumbnail': 'https://gfx.nrk.no/D2u6-EyVUZpVCq0PdSNHRgdBZCV40ekpk6s9fZWiMtyg',
            'season_number': 2014,
            'season_id': '39240',
            'alt_title': 'Grunnlovsjubiléet - Stor ståhei for ingenting',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # single playlist video
        'url': 'https://tv.nrk.no/serie/tour-de-ski/MSPO40010515/06-01-2015#del=2',
        'info_dict': {
            'id': 'MSPO40010515',
            'ext': 'mp4',
            'title': 'Tour de Ski - Sprint fri teknikk, kvinner og menn',
            'description': 'md5:1f97a41f05a9486ee00c56f35f82993d',
            'age_limit': 0,
            'episode': 'Sprint fri teknikk, kvinner og menn',
            'series': 'Tour de Ski',
            'thumbnail': 'https://gfx.nrk.no/s9vNwGPGN-Un-UCvitD09we9HRLDxisnipA9K__d5c3Q',
            'season_id': '53512',
            'chapters': [
                {'start_time': 0, 'end_time': 6938.0, 'title': '<Untitled Chapter 1>'},
                {'start_time': 6938.0, 'end_time': 6947.52, 'title': 'Outro'},
            ],
            'season_number': 2015,
            'episode_number': 5,
            'upload_date': '20150106',
            'duration': 6947.52,
            'timestamp': 1420545563,
            'alt_title': 'Sprint fri teknikk, kvinner og menn',
            'season': 'Season 2015',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://tv.nrk.no/serie/tour-de-ski/MSPO40010515/06-01-2015',
        'info_dict': {
            'id': 'MSPO40010515',
            'ext': 'mp4',
            'title': 'Tour de Ski - Sprint fri teknikk, kvinner og menn',
            'description': 'md5:1f97a41f05a9486ee00c56f35f82993d',
            'age_limit': 0,
            'episode': 'Sprint fri teknikk, kvinner og menn',
            'series': 'Tour de Ski',
            'thumbnail': 'https://gfx.nrk.no/s9vNwGPGN-Un-UCvitD09we9HRLDxisnipA9K__d5c3Q',
            'season_id': '53512',
            'chapters': [
                {'start_time': 0, 'end_time': 6938.0, 'title': '<Untitled Chapter 1>'},
                {'start_time': 6938.0, 'end_time': 6947.52, 'title': 'Outro'},
            ],
            'season_number': 2015,
            'episode_number': 5,
            'upload_date': '20150106',
            'duration': 6947.52,
            'timestamp': 1420545563,
            'alt_title': 'Sprint fri teknikk, kvinner og menn',
            'season': 'Season 2015',
        },
        'expected_warnings': ['Failed to download m3u8 information'],
        'skip': 'Ikke tilgjengelig utenfor Norge',
    }, {
        'url': 'https://tv.nrk.no/serie/anno/KMTE50001317/sesong-3/episode-13',
        'info_dict': {
            'id': 'KMTE50001317',
            'ext': 'mp4',
            'title': 'Anno - 13. episode',
            'description': 'md5:11d9613661a8dbe6f9bef54e3a4cbbfa',
            'duration': 2340,
            'series': 'Anno',
            'episode': '13. episode',
            'season_number': 3,
            'episode_number': 13,
            'age_limit': 0,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'ProgramRightsHasExpired',
    }, {
        'url': 'https://tv.nrk.no/serie/nytt-paa-nytt/MUHH46000317/27-01-2017',
        'info_dict': {
            'id': 'MUHH46000317',
            'ext': 'mp4',
            'title': 'Nytt på Nytt 27.01.2017',
            'description': 'md5:5358d6388fba0ea6f0b6d11c48b9eb4b',
            'duration': 1796,
            'series': 'Nytt på nytt',
            'episode': '27.01.2017',
            'age_limit': 0,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'ProgramRightsHasExpired',
    }, {
        'url': 'https://radio.nrk.no/serie/dagsnytt/NPUB21019315/12-07-2015#',
        'only_matching': True,
    }, {
        'url': 'https://tv.nrk.no/serie/lindmo/2018/MUHU11006318/avspiller',
        'only_matching': True,
    }, {
        'url': 'https://radio.nrk.no/serie/dagsnytt/sesong/201507/NPUB21019315',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            f'nrk:{video_id}', ie=NRKIE.ie_key(), video_id=video_id)


class NRKTVEpisodeIE(NRKBaseIE):
    _VALID_URL = r'https?://tv\.nrk\.no/serie/(?P<id>[^/]+/sesong/(?P<season_number>\d+)/episode/(?P<episode_number>\d+))'
    _TESTS = [{
        'url': 'https://tv.nrk.no/serie/hellums-kro/sesong/1/episode/2',
        'info_dict': {
            'id': 'MUHH36005220',
            'ext': 'mp4',
            'title': 'Hellums kro - 2. Kro, krig og kjærlighet',
            'description': 'md5:b32a7dc0b1ed27c8064f58b97bda4350',
            'duration': 1563.92,
            'series': 'Hellums kro',
            'season_number': 1,
            'episode_number': 2,
            'episode': '2. Kro, krig og kjærlighet',
            'age_limit': 6,
            'timestamp': 1572584520,
            'upload_date': '20191101',
            'thumbnail': 'https://gfx.nrk.no/2_4mhU2JhR-8IYRC_OMmAQDbbOHgwcHqgi2sBrNrsjkg',
            'alt_title': '2. Kro, krig og kjærlighet',
            'season': 'Season 1',
            'season_id': '124163',
            'chapters': [
                {'start_time': 0, 'end_time': 29.0, 'title': '<Untitled Chapter 1>'},
                {'start_time': 29.0, 'end_time': 50.0, 'title': 'Intro'},
                {'start_time': 1530.0, 'end_time': 1563.92, 'title': 'Outro'},
            ],
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://tv.nrk.no/serie/backstage/sesong/1/episode/8',
        'info_dict': {
            'id': 'MSUI14000816',
            'ext': 'mp4',
            'title': 'Backstage - 8. episode',
            'description': 'md5:de6ca5d5a2d56849e4021f2bf2850df4',
            'duration': 1320,
            'series': 'Backstage',
            'season_number': 1,
            'episode_number': 8,
            'episode': '8. episode',
            'age_limit': 0,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'ProgramRightsHasExpired',
    }]

    def _real_extract(self, url):
        # HEADRequest(url) only works if a regular GET request was recently made by anyone for the specific URL being requested.
        response = self._request_webpage(url, None, expected_status=True)

        nrk_id = self._match_id(url)

        return self.url_result(
            response.url, NRKTVIE.ie_key(), nrk_id, url_transparent=True,
        )


class NRKTVSerieBaseIE(NRKBaseIE):
    def _extract_entries(self, entry_list):
        if not isinstance(entry_list, list):
            return []
        entries = []
        for episode in entry_list:
            nrk_id = episode.get('prfId') or episode.get('episodeId')
            if traverse_obj(episode, ('availability', 'status')) == 'expired':
                self.report_warning(episode['availability'].get('label'), nrk_id)
                continue
            if not nrk_id or not isinstance(nrk_id, str):
                continue
            entries.append(self.url_result(
                f'nrk:{nrk_id}', ie=NRKIE.ie_key(), video_id=nrk_id))
        return entries

    _ASSETS_KEYS = ('episodes', 'instalments')

    def _extract_assets_key(self, embedded):
        for asset_key in self._ASSETS_KEYS:
            if embedded.get(asset_key):
                return asset_key

    @staticmethod
    def _catalog_name(serie_kind):
        return 'podcast' if serie_kind in ('podcast', 'podkast') else 'series'

    def _entries(self, data, display_id):
        for page_num in itertools.count(1):
            embedded = data.get('_embedded') or data
            if not isinstance(embedded, dict):
                break
            assets_key = self._extract_assets_key(embedded)
            if not assets_key:
                break
            # Extract entries
            entries = traverse_obj(
                embedded,
                (assets_key, '_embedded', assets_key, {list}),
                (assets_key, {list}),
            )
            yield from self._extract_entries(entries)
            # Find next URL
            next_url_path = traverse_obj(
                data,
                ('_links', 'next', 'href'),
                ('_embedded', assets_key, '_links', 'next', 'href'),
            )
            if not next_url_path:
                break
            data = self._call_api(
                next_url_path, display_id,
                note=f'Downloading {assets_key} JSON page {page_num}',
                fatal=False)
            if not data:
                break


class NRKTVSeasonIE(NRKTVSerieBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?P<domain>tv|radio)\.nrk\.no/
                        (?P<serie_kind>serie|pod[ck]ast)/
                        (?P<serie>[^/]+)/
                        (?:
                            (?:sesong/)?(?P<id>\d+)|
                            sesong/(?P<id_2>[^/?#&]+)
                        )
                    '''
    _TESTS = [{
        'url': 'https://tv.nrk.no/serie/backstage/sesong/1',
        'info_dict': {
            'id': 'backstage/1',
            'title': 'Sesong 1',
        },
        'playlist_mincount': 30,
    }, {
        'url': 'https://tv.nrk.no/serie/presten/sesong/ekstramateriale',
        'info_dict': {
            'id': 'MUHH47005117',
            'ext': 'mp4',
            'description': '',
            'thumbnail': 'https://gfx.nrk.no/sJZroQqD2P8wGMMl5ADznwqiIlAXaCpNofA2pIhe3udA',
            'alt_title': 'Bloopers: Episode 1',
            'chapters': [
                {'start_time': 0, 'end_time': 356.0, 'title': '<Untitled Chapter 1>'},
                {'start_time': 356.0, 'end_time': 365.8, 'title': 'Outro'},
            ],
            'upload_date': '20180302',
            'timestamp': 1519966800,
            'title': 'Presten',
            'age_limit': 0,
            'duration': 365.8,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # no /sesong/ in path
        'url': 'https://tv.nrk.no/serie/lindmo/2016',
        'info_dict': {
            'id': 'lindmo/2016',
            'title': '2016',
        },
        'playlist_mincount': 29,
    }, {
        # weird nested _embedded in catalog JSON response
        'url': 'https://radio.nrk.no/serie/dickie-dick-dickens/sesong/1',
        'info_dict': {
            'id': 'dickie-dick-dickens/1',
            'title': 'Sesong 1',
        },
        'playlist_mincount': 11,
    }, {
        # 841 entries, multi page
        'url': 'https://radio.nrk.no/serie/dagsnytt/sesong/201509',
        'info_dict': {
            'id': 'dagsnytt/201509',
            'title': 'September 2015',
        },
        'playlist_mincount': 841,
        'skip': 'ProgramRightsHasExpired',
    }, {
        # 180 entries, single page
        'url': 'https://tv.nrk.no/serie/spangas/sesong/1',
        'only_matching': True,
    }, {
        'url': 'https://radio.nrk.no/podkast/hele_historien/sesong/diagnose-kverulant',
        'info_dict': {
            'id': 'hele_historien/diagnose-kverulant',
            'title': 'Diagnose kverulant',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'https://radio.nrk.no/podkast/loerdagsraadet/sesong/202101',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return (False if NRKTVIE.suitable(url) or NRKTVEpisodeIE.suitable(url) or NRKRadioPodkastIE.suitable(url)
                else super().suitable(url))

    def _real_extract(self, url):
        domain, serie_kind, serie, season_id, season_id_2 = self._match_valid_url(url).group(
            'domain', 'serie_kind', 'serie', 'id', 'id_2')
        season_id = season_id or season_id_2
        display_id = f'{serie}/{season_id}'

        api_suffix = f'/seasons/{season_id}' if season_id != 'ekstramateriale' else '/extramaterial'

        data = self._call_api(
            f'{domain}/catalog/{self._catalog_name(serie_kind)}/{serie}{api_suffix}',
            display_id, 'season', query={'pageSize': 50})

        return self.playlist_result(
            self._entries(data, display_id), display_id,
            title=traverse_obj(data, ('titles', 'title', {str})))


class NRKTVSeriesIE(NRKTVSerieBaseIE):
    _VALID_URL = r'https?://(?P<domain>(?:tv|radio)\.nrk|(?:tv\.)?nrksuper)\.no/(?P<serie_kind>serie|pod[ck]ast)/(?P<id>[^/]+)'
    _TESTS = [{
        # new layout, instalments
        'url': 'https://tv.nrk.no/serie/groenn-glede',
        'info_dict': {
            'id': 'groenn-glede',
            'title': 'Grønn glede',
            'description': 'md5:7576e92ae7f65da6993cf90ee29e4608',
        },
        'playlist_mincount': 90,
    }, {
        # new layout, instalments, more entries
        'url': 'https://tv.nrk.no/serie/lindmo',
        'only_matching': True,
    }, {
        'url': 'https://tv.nrk.no/serie/blank',
        'info_dict': {
            'id': 'blank',
            'title': 'Blank',
            'description': 'md5:7664b4e7e77dc6810cd3bca367c25b6e',
        },
        'playlist_mincount': 30,
    }, {
        # new layout, seasons
        'url': 'https://tv.nrk.no/serie/backstage',
        'info_dict': {
            'id': 'backstage',
            'title': 'Backstage',
            'description': 'md5:63692ceb96813d9a207e9910483d948b',
        },
        'playlist_mincount': 60,
    }, {
        # old layout
        'url': 'https://tv.nrksuper.no/serie/labyrint',
        'info_dict': {
            'id': 'labyrint',
            'title': 'Labyrint',
            'description': 'I Daidalos sin undersjøiske Labyrint venter spennende oppgaver, skumle robotskapninger og slim.',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'https://tv.nrk.no/serie/broedrene-dal-og-spektralsteinene',
        'only_matching': True,
    }, {
        'url': 'https://tv.nrk.no/serie/saving-the-human-race',
        'only_matching': True,
    }, {
        'url': 'https://tv.nrk.no/serie/postmann-pat',
        'only_matching': True,
    }, {
        'url': 'https://radio.nrk.no/serie/dickie-dick-dickens',
        'info_dict': {
            'id': 'dickie-dick-dickens',
            'title': 'Dickie Dick Dickens',
            'description': 'md5:605464fab26d06b1ce6a11c3ea37d36d',
        },
        'playlist_mincount': 8,
    }, {
        'url': 'https://nrksuper.no/serie/labyrint',
        'only_matching': True,
    }, {
        'url': 'https://radio.nrk.no/podkast/ulrikkes_univers',
        'info_dict': {
            'id': 'ulrikkes_univers',
            'title': 'Ulrikkes univers',
            'description': 'md5:8af9fc2ee4aecd7f91777383fde50dcc',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://radio.nrk.no/podkast/ulrikkes_univers/nrkno-poddkast-26588-134079-05042018030000',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return (
            False if any(ie.suitable(url)
                         for ie in (NRKTVIE, NRKTVEpisodeIE, NRKRadioPodkastIE, NRKTVSeasonIE))
            else super().suitable(url))

    def _real_extract(self, url):
        site, serie_kind, series_id = self._match_valid_url(url).groups()
        is_radio = site == 'radio.nrk'
        domain = 'radio' if is_radio else 'tv'

        size_prefix = 'p' if is_radio else 'embeddedInstalmentsP'
        series = self._call_api(
            f'{domain}/catalog/{self._catalog_name(serie_kind)}/{series_id}',
            series_id, 'serie', query={size_prefix + 'ageSize': 50})
        titles = traverse_obj(
            series,
            (..., 'titles'),
            (..., 'type', 'titles'),
            (..., 'seriesType', 'titles'),
            get_all=False,

        )
        entries = []
        entries.extend(self._entries(series, series_id))
        embedded = series.get('_embedded') or {}
        linked_seasons = traverse_obj(series, ('_links', 'seasons')) or []
        embedded_seasons = embedded.get('seasons') or []
        if len(linked_seasons) > len(embedded_seasons):
            for season in linked_seasons:
                season_url = urljoin(url, season.get('href'))
                if not season_url:
                    season_name = season.get('name')
                    if season_name and isinstance(season_name, str):
                        season_url = f'https://{domain}.nrk.no/serie/{series_id}/sesong/{season_name}'
                if season_url:
                    entries.append(self.url_result(
                        season_url, ie=NRKTVSeasonIE.ie_key(),
                        video_title=season.get('title')))
        else:
            for season in embedded_seasons:
                entries.extend(self._entries(season, series_id))
        entries.extend(self._entries(
            embedded.get('extraMaterial') or {}, series_id))

        return self.playlist_result(
            entries, series_id, titles.get('title'), titles.get('subtitle'))


class NRKTVDirekteIE(NRKBaseIE):
    IE_DESC = 'NRK TV Direkte and NRK Radio Direkte'
    _VALID_URL = r'https?://(?:tv|radio)\.nrk\.no/direkte/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://tv.nrk.no/direkte/nrk1',
        'only_matching': True,
    }, {
        'url': 'https://radio.nrk.no/direkte/p1_oslo_akershus',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            f'nrk:{video_id}', ie=NRKIE.ie_key(), video_id=video_id)


class NRKRadioPodkastIE(NRKBaseIE):
    _VALID_URL = r'https?://radio\.nrk\.no/pod[ck]ast/(?:[^/]+/)+(?P<id>l_[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'

    _TESTS = [{
        'url': 'https://radio.nrk.no/podkast/ulrikkes_univers/l_96f4f1b0-de54-4e6a-b4f1-b0de54fe6af8',
        'md5': 'a68c3564be2f4426254f026c95a06348',
        'info_dict': {
            'id': 'l_96f4f1b0-de54-4e6a-b4f1-b0de54fe6af8',
            'ext': 'mp3',
            'timestamp': 1522897200,
            'alt_title': 'md5:06eae9f8c8ccf0718b54c83654e65550',
            'upload_date': '20180405',
            'thumbnail': 'https://gfx.nrk.no/CEDlVkEKxLYiBZ-CXjxSxgduDdaL-a4XTZlar9AoJFOA',
            'description': '',
            'title': 'Jeg er sinna og det må du tåle!',
            'age_limit': 0,
            'duration': 1682.0,
        },
    }, {
        'url': 'https://radio.nrk.no/podcast/ulrikkes_univers/l_96f4f1b0-de54-4e6a-b4f1-b0de54fe6af8',
        'only_matching': True,
    }, {
        'url': 'https://radio.nrk.no/podkast/ulrikkes_univers/sesong/1/l_96f4f1b0-de54-4e6a-b4f1-b0de54fe6af8',
        'only_matching': True,
    }, {
        'url': 'https://radio.nrk.no/podkast/hele_historien/sesong/bortfoert-i-bergen/l_774d1a2c-7aa7-4965-8d1a-2c7aa7d9652c',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            f'nrk:{video_id}', ie=NRKIE.ie_key(), video_id=video_id)


class NRKPlaylistBaseIE(NRKBaseIE):
    def _extract_description(self, webpage):
        pass

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        # Uses the render HTML endpoint instead of the regular article URL to prevent unrelated videos from being downloaded
        # if .rich[data-video-id] elements appear in the "related articles" section too instead of just the main article.
        webpage = self._download_webpage(f'https://www.nrk.no/serum/api/render/{playlist_id.split("-")[-1]}', playlist_id)
        entries = [
            self.url_result(f'nrk:{video_id}', NRKIE.ie_key())
            for video_id in re.findall(self._ITEM_RE, webpage)
        ]

        playlist_title = self._extract_title(webpage)
        playlist_description = self._extract_description(webpage)

        return self.playlist_result(
            entries, playlist_id, playlist_title, playlist_description)


class NRKPlaylistIE(NRKPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?nrk\.no/(?!video|skole)(?:[^/]+/)+(?P<id>[^/]+)'
    _ITEM_RE = r'class="[^"]*\brich\b[^"]*"[^>]+data-video-id="([^"]+)"'
    _TITLE_RE = r'class="[^"]*\barticle-title\b[^"]*"[^>]*>([^<]+)<'
    _DESCRIPTION_RE = r'class="[^"]*[\s"]article-lead[\s"][^>]*>[^<]*<p>([^<]*)<'
    _TESTS = [{
        'url': 'http://www.nrk.no/troms/gjenopplev-den-historiske-solformorkelsen-1.12270763',
        'info_dict': {
            'id': 'gjenopplev-den-historiske-solformorkelsen-1.12270763',
            'title': 'Gjenopplev den historiske solformørkelsen',
            'description': 'md5:c2df8ea3bac5654a26fc2834a542feed',
        },
        'playlist_count': 2,
    }, {
        'url': 'http://www.nrk.no/kultur/bok/rivertonprisen-til-karin-fossum-1.12266449',
        'info_dict': {
            'id': 'rivertonprisen-til-karin-fossum-1.12266449',
            'title': 'Rivertonprisen til Karin Fossum',
            'description': 'Første kvinne på 15 år til å vinne krimlitteraturprisen.',
        },
        'playlist_count': 2,
    }]

    def _extract_title(self, webpage):
        return re.search(self._TITLE_RE, webpage).group(1)

    def _extract_description(self, webpage):
        return re.search(self._DESCRIPTION_RE, webpage).group(1)


class NRKSkoleIE(NRKBaseIE):
    IE_DESC = 'NRK Skole'
    _VALID_URL = r'https?://(?:www\.)?nrk\.no/skole/?\?.*\bmediaId=(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.nrk.no/skole/?page=search&q=&mediaId=14099',
        'md5': '1d54ec4cff70d8f2c7909d1922514af2',
        'info_dict': {
            'id': '6021',
            'ext': 'mp4',
            'title': 'Genetikk og eneggede tvillinger',
            'description': 'md5:7c0cc42d35d99bbc58f45639cdbcc163',
            'duration': 399,
            'thumbnail': 'https://gfx.nrk.no/5SN-Uq11iR3ADwrCwTv0bAKbbBXXNpVJsaCLGiU8lFoQ',
            'timestamp': 1205622000,
            'upload_date': '20080315',
            'alt_title': '',
        },
    }, {
        'url': 'https://www.nrk.no/skole/?page=objectives&subject=naturfag&objective=K15114&mediaId=19355',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        response = self._download_json(
            f'https://nrkno-skole-prod.kube.nrk.no/skole/api/media/{video_id}',
            video_id)
        nrk_id = response['psId']
        return self.url_result(
            f'nrk:{nrk_id}', NRKIE, nrk_id, url_transparent=True,
            **traverse_obj(response, {
                'title': ('title', {str}),
                'timestamp': ('airedDate', {parse_iso8601}),
                'description': ('summary', {str}),
            }))
