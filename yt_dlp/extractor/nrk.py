import itertools
import random
import re

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    parse_duration,
    parse_iso8601,
    str_or_none,
    try_get,
    update_url_query,
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

    def _extract_nrk_formats(self, asset_url, video_id):
        asset_url = update_url_query(asset_url, {
            # Remove 'adap' to return all streams (known values are: small, large, small_h265, large_h265)
            'adap': [],
            # Disable subtitles since they are fetched separately
            's': 0,
        })
        if re.match(r'https?://[^/]+\.akamaihd\.net/i/', asset_url):
            return self._extract_akamai_formats(asset_url, video_id)
        asset_url = re.sub(r'(?:bw_(?:low|high)=\d+|no_audio_only)&?', '', asset_url)
        formats = self._extract_m3u8_formats(
            asset_url, video_id, 'mp4', 'm3u8_native', fatal=False)
        if not formats and re.search(self._CDN_REPL_REGEX, asset_url):
            formats = self._extract_m3u8_formats(
                re.sub(self._CDN_REPL_REGEX, '://nrk-od-%02d.akamaized.net/no/' % random.randint(0, 99), asset_url),
                video_id, 'mp4', 'm3u8_native', fatal=False)
        return formats

    def _raise_error(self, data):
        MESSAGES = {
            'ProgramRightsAreNotReady': 'Du kan dessverre ikke se eller høre programmet',
            'ProgramRightsHasExpired': 'Programmet har gått ut',
            'NoProgramRights': 'Ikke tilgjengelig',
            'ProgramIsGeoBlocked': 'NRK har ikke rettigheter til å vise dette programmet utenfor Norge',
        }
        message_type = data.get('messageType', '')
        # Can be ProgramIsGeoBlocked or ChannelIsGeoBlocked*
        if 'IsGeoBlocked' in message_type or try_get(data, lambda x: x['usageRights']['isGeoBlocked']) is True:
            self.raise_geo_restricted(
                msg=MESSAGES.get('ProgramIsGeoBlocked'),
                countries=self._GEO_COUNTRIES)
        message = data.get('endUserMessage') or MESSAGES.get(message_type, message_type)
        raise ExtractorError(f'{self.IE_NAME} said: {message}', expected=True)

    def _call_api(self, path, video_id, item=None, note=None, fatal=True, query=None):
        return self._download_json(
            urljoin('https://psapi.nrk.no/', path),
            video_id, note or f'Downloading {item} JSON',
            fatal=fatal, query=query, headers={
                # Needed for working stream URLs, see https://github.com/yt-dlp/yt-dlp/issues/12192
                'Accept': 'application/vnd.nrk.psapi+json; version=9; player=tv-player; device=player-core',
            })


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
            'upload_date': '20140325',
            'thumbnail': r're:^https?://gfx\.nrk\.no/.*$',
            'timestamp': 1395751833,
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
            'timestamp': 1398429565,
            'alt_title': 'Cathrine Lie Wathne er blind, og bruker hurtigtaster for å navigere seg rundt på ulike nettsider.',
            'thumbnail': 'https://gfx.nrk.no/urxQMSXF-WnbfjBH5ke2igLGyN27EdJVWZ6FOsEAclhA',
            'upload_date': '20140425',
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

        def call_playback_api(item, query=None):
            try:
                return self._call_api(f'playback/{item}/program/{video_id}', video_id, item, query=query)
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                    return self._call_api(f'playback/{item}/{video_id}', video_id, item, query=query)
                raise

        # known values for preferredCdn: akamai, globalconnect and telenor
        manifest = call_playback_api('manifest', {'preferredCdn': 'akamai'})

        video_id = try_get(manifest, lambda x: x['id'], str) or video_id

        if manifest.get('playability') == 'nonPlayable':
            self._raise_error(manifest['nonPlayable'])

        playable = manifest['playable']

        formats = []
        for asset in playable['assets']:
            if not isinstance(asset, dict):
                continue
            if asset.get('encrypted'):
                continue
            format_url = url_or_none(asset.get('url'))
            if not format_url:
                continue
            asset_format = (asset.get('format') or '').lower()
            if asset_format == 'hls' or determine_ext(format_url) == 'm3u8':
                formats.extend(self._extract_nrk_formats(format_url, video_id))
            elif asset_format == 'mp3':
                formats.append({
                    'url': format_url,
                    'format_id': asset_format,
                    'vcodec': 'none',
                })

        data = call_playback_api('metadata')

        preplay = data['preplay']
        titles = preplay['titles']
        title = titles['title']
        alt_title = titles.get('subtitle')

        description = try_get(preplay, lambda x: x['description'].replace('\r', '\n'))
        duration = parse_duration(playable.get('duration')) or parse_duration(data.get('duration'))

        thumbnails = []
        for image in try_get(
                preplay, lambda x: x['poster']['images'], list) or []:
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

        subtitles = {}
        for sub in try_get(playable, lambda x: x['subtitles'], list) or []:
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

        legal_age = try_get(
            data, lambda x: x['legalAge']['body']['rating']['code'], str)
        # https://en.wikipedia.org/wiki/Norwegian_Media_Authority
        age_limit = None
        if legal_age:
            if legal_age == 'A':
                age_limit = 0
            elif legal_age.isdigit():
                age_limit = int_or_none(legal_age)

        is_series = try_get(data, lambda x: x['_links']['series']['name']) == 'series'

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
            'timestamp': parse_iso8601(try_get(manifest, lambda x: x['availability']['onDemand']['from'], str)),
        }

        if is_series:
            series = season_id = season_number = episode = episode_number = None
            programs = self._call_api(
                f'programs/{video_id}', video_id, 'programs', fatal=False)
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


class NRKTVIE(InfoExtractor):
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
            'series': '20 spørsmål',
            'episode': '23. mai 2014',
            'age_limit': 0,
            'timestamp': 1584593700,
            'thumbnail': 'https://gfx.nrk.no/u7uCe79SEfPVGRAGVp2_uAZnNc4mfz_kjXg6Bgek8lMQ',
            'season_id': '126936',
            'upload_date': '20200319',
            'season': 'Season 2014',
            'season_number': 2014,
            'episode_number': 3,
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
            'title': 'Sprint fri teknikk, kvinner og menn 06.01.2015',
            'description': 'md5:c03aba1e917561eface5214020551b7a',
            'age_limit': 0,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Failed to download m3u8 information'],
        'skip': 'particular part is not supported currently',
    }, {
        'url': 'https://tv.nrk.no/serie/tour-de-ski/MSPO40010515/06-01-2015',
        'info_dict': {
            'id': 'MSPO40010515',
            'ext': 'mp4',
            'title': 'Sprint fri teknikk, kvinner og menn 06.01.2015',
            'description': 'md5:c03aba1e917561eface5214020551b7a',
            'age_limit': 0,
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


class NRKTVEpisodeIE(InfoExtractor):
    _VALID_URL = r'https?://tv\.nrk\.no/serie/(?P<id>[^/?#]+/sesong/(?P<season_number>\d+)/episode/(?P<episode_number>\d+))'
    _TESTS = [{
        'url': 'https://tv.nrk.no/serie/hellums-kro/sesong/1/episode/2',
        'add_ie': [NRKIE.ie_key()],
        'info_dict': {
            'id': 'MUHH36005220',
            'ext': 'mp4',
            'title': 'Hellums kro - 2. Kro, krig og kjærlighet',
            'description': 'md5:ad92ddffc04cea8ce14b415deef81787',
            'duration': 1563.92,
            'series': 'Hellums kro',
            'season_number': 1,
            'episode_number': 2,
            'episode': '2. Kro, krig og kjærlighet',
            'age_limit': 6,
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
        display_id, season_number, episode_number = self._match_valid_url(url).group(
            'id', 'season_number', 'episode_number')
        webpage, urlh = self._download_webpage_handle(url, display_id)

        if NRKTVIE.suitable(urlh.url):
            nrk_id = NRKTVIE._match_id(urlh.url)
        else:
            nrk_id = self._search_json(
                r'<script\b[^>]+\bid="pageData"[^>]*>', webpage,
                'page data', display_id)['initialState']['selectedEpisodePrfId']
            if not re.fullmatch(NRKTVIE._EPISODE_RE, nrk_id):
                raise ExtractorError('Unable to extract NRK ID')

        return self.url_result(
            f'nrk:{nrk_id}', NRKIE, nrk_id,
            season_number=int(season_number),
            episode_number=int(episode_number))


class NRKTVSerieBaseIE(NRKBaseIE):
    def _extract_entries(self, entry_list):
        if not isinstance(entry_list, list):
            return []
        entries = []
        for episode in entry_list:
            nrk_id = episode.get('prfId') or episode.get('episodeId')
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
            entries = try_get(
                embedded,
                (lambda x: x[assets_key]['_embedded'][assets_key],
                 lambda x: x[assets_key]),
                list)
            yield from self._extract_entries(entries)
            # Find next URL
            next_url_path = try_get(
                data,
                (lambda x: x['_links']['next']['href'],
                 lambda x: x['_embedded'][assets_key]['_links']['next']['href']),
                str)
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
        mobj = self._match_valid_url(url)
        domain = mobj.group('domain')
        serie_kind = mobj.group('serie_kind')
        serie = mobj.group('serie')
        season_id = mobj.group('id') or mobj.group('id_2')
        display_id = f'{serie}/{season_id}'

        data = self._call_api(
            f'{domain}/catalog/{self._catalog_name(serie_kind)}/{serie}/seasons/{season_id}',
            display_id, 'season', query={'pageSize': 50})

        title = try_get(data, lambda x: x['titles']['title'], str) or display_id
        return self.playlist_result(
            self._entries(data, display_id),
            display_id, title)


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
            'description': 'md5:19e67411ffe57f7dce08a943d7a0b91f',
        },
        'playlist_mincount': 8,
    }, {
        'url': 'https://nrksuper.no/serie/labyrint',
        'only_matching': True,
    }, {
        'url': 'https://radio.nrk.no/podkast/ulrikkes_univers',
        'info_dict': {
            'id': 'ulrikkes_univers',
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
        titles = try_get(series, [
            lambda x: x['titles'],
            lambda x: x[x['type']]['titles'],
            lambda x: x[x['seriesType']]['titles'],
        ]) or {}

        entries = []
        entries.extend(self._entries(series, series_id))
        embedded = series.get('_embedded') or {}
        linked_seasons = try_get(series, lambda x: x['_links']['seasons']) or []
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


class NRKTVDirekteIE(NRKTVIE):  # XXX: Do not subclass from concrete IE
    IE_DESC = 'NRK TV Direkte and NRK Radio Direkte'
    _VALID_URL = r'https?://(?:tv|radio)\.nrk\.no/direkte/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://tv.nrk.no/direkte/nrk1',
        'only_matching': True,
    }, {
        'url': 'https://radio.nrk.no/direkte/p1_oslo_akershus',
        'only_matching': True,
    }]


class NRKRadioPodkastIE(InfoExtractor):
    _VALID_URL = r'https?://radio\.nrk\.no/pod[ck]ast/(?:[^/]+/)+(?P<id>l_[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'

    _TESTS = [{
        'url': 'https://radio.nrk.no/podkast/ulrikkes_univers/l_96f4f1b0-de54-4e6a-b4f1-b0de54fe6af8',
        'md5': '8d40dab61cea8ab0114e090b029a0565',
        'info_dict': {
            'id': 'MUHH48000314AA',
            'ext': 'mp4',
            'title': '20 spørsmål 23.05.2014',
            'description': 'md5:bdea103bc35494c143c6a9acdd84887a',
            'duration': 1741,
            'series': '20 spørsmål',
            'episode': '23.05.2014',
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


class NRKPlaylistBaseIE(InfoExtractor):
    def _extract_description(self, webpage):
        pass

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

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
        return self._og_search_title(webpage, fatal=False)

    def _extract_description(self, webpage):
        return self._og_search_description(webpage)


class NRKTVEpisodesIE(NRKPlaylistBaseIE):
    _VALID_URL = r'https?://tv\.nrk\.no/program/[Ee]pisodes/[^/]+/(?P<id>\d+)'
    _ITEM_RE = rf'data-episode=["\']{NRKTVIE._EPISODE_RE}'
    _TESTS = [{
        'url': 'https://tv.nrk.no/program/episodes/nytt-paa-nytt/69031',
        'info_dict': {
            'id': '69031',
            'title': 'Nytt på nytt, sesong: 201210',
        },
        'playlist_count': 4,
    }]

    def _extract_title(self, webpage):
        return self._html_search_regex(
            r'<h1>([^<]+)</h1>', webpage, 'title', fatal=False)


class NRKSkoleIE(InfoExtractor):
    IE_DESC = 'NRK Skole'
    _VALID_URL = r'https?://(?:www\.)?nrk\.no/skole/?\?.*\bmediaId=(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.nrk.no/skole/?page=search&q=&mediaId=14099',
        'md5': '18c12c3d071953c3bf8d54ef6b2587b7',
        'info_dict': {
            'id': '6021',
            'ext': 'mp4',
            'title': 'Genetikk og eneggede tvillinger',
            'description': 'md5:3aca25dcf38ec30f0363428d2b265f8d',
            'duration': 399,
        },
    }, {
        'url': 'https://www.nrk.no/skole/?page=objectives&subject=naturfag&objective=K15114&mediaId=19355',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        nrk_id = self._download_json(
            f'https://nrkno-skole-prod.kube.nrk.no/skole/api/media/{video_id}',
            video_id)['psId']

        return self.url_result(f'nrk:{nrk_id}')
