import itertools
import json
import re
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    ISO639Utils,
    determine_ext,
    filter_dict,
    float_or_none,
    int_or_none,
    join_nonempty,
    make_archive_id,
    parse_codecs,
    parse_iso8601,
    parse_qs,
    smuggle_url,
    unified_timestamp,
    unsmuggle_url,
    url_or_none,
    urljoin,
    variadic,
)
from ..utils.traversal import require, traverse_obj


class ZDFBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['DE']
    _TOKEN_CACHE_PARAMS = ('zdf', 'api-token')
    _token_cache = {}

    def _get_api_token(self):
        # As of 2025-03, this API is used by the Android app for getting tokens.
        # An equivalent token could be extracted from the webpage should the API become unavailable.
        # For now this allows the extractor to avoid dealing with Next.js hydration data.
        if not self._token_cache:
            self._token_cache.update(self.cache.load(*self._TOKEN_CACHE_PARAMS, default={}))

        if traverse_obj(self._token_cache, ('expires', {int_or_none}), default=0) < int(time.time()):
            self._token_cache.update(self._download_json(
                'https://zdf-prod-futura.zdf.de/mediathekV2/token', None,
                'Downloading API token', 'Failed to download API token'))
            self.cache.store(*self._TOKEN_CACHE_PARAMS, self._token_cache)

        return f'{self._token_cache["type"]} {self._token_cache["token"]}'

    def _call_api(self, url, video_id, item, api_token=None):
        return self._download_json(
            url, video_id, f'Downloading {item}', f'Failed to download {item}',
            headers=filter_dict({'Api-Auth': api_token}))

    def _parse_aspect_ratio(self, aspect_ratio):
        if not aspect_ratio or not isinstance(aspect_ratio, str):
            return None
        mobj = re.match(r'(?P<width>\d+):(?P<height>\d+)', aspect_ratio)
        return int(mobj.group('width')) / int(mobj.group('height')) if mobj else None

    def _extract_chapters(self, data):
        return traverse_obj(data, (lambda _, v: v['anchorOffset'], {
            'start_time': ('anchorOffset', {float_or_none}),
            'title': ('anchorLabel', {str}),
        })) or None

    @staticmethod
    def _extract_subtitles(src):
        seen_urls = set()
        subtitles = {}
        for caption in src:
            subtitle_url = url_or_none(caption.get('uri'))
            if not subtitle_url or subtitle_url in seen_urls:
                continue
            seen_urls.add(subtitle_url)
            lang = caption.get('language') or 'deu'
            subtitles.setdefault(lang, []).append({
                'url': subtitle_url,
            })
        return subtitles

    def _expand_ptmd_template(self, api_base_url, template):
        return urljoin(api_base_url, template.replace('{playerId}', 'android_native_6'))

    def _extract_ptmd(self, ptmd_urls, video_id, api_token=None, aspect_ratio=None):
        content_id = None
        duration = None
        formats, src_captions = [], []
        seen_urls = set()

        for ptmd_url in variadic(ptmd_urls):
            ptmd_url, smuggled_data = unsmuggle_url(ptmd_url, {})
            # Is it a DGS variant? (*D*eutsche *G*ebärden*s*prache' / German Sign Language)
            is_dgs = smuggled_data.get('vod_media_type') == 'DGS'
            ptmd = self._call_api(ptmd_url, video_id, 'PTMD data', api_token)

            basename = (
                ptmd.get('basename')
                # ptmd_url examples:
                # https://api.zdf.de/tmd/2/android_native_6/vod/ptmd/mediathek/250328_sendung_hsh/3
                # https://tmd.phoenix.de/tmd/2/android_native_6/vod/ptmd/phoenix/221215_phx_spitzbergen
                or self._search_regex(r'/vod/ptmd/[^/?#]+/(\w+)', ptmd_url, 'content ID', default=None))
            # If this is_dgs, then it's from ZDFIE and it only uses content_id for _old_archive_ids,
            # and the old version of the extractor didn't extract DGS variants, so ignore basename
            if not content_id and not is_dgs:
                content_id = basename

            if not duration:
                duration = traverse_obj(ptmd, ('attributes', 'duration', 'value', {float_or_none(scale=1000)}))
            src_captions += traverse_obj(ptmd, ('captions', ..., {dict}))

            for stream in traverse_obj(ptmd, ('priorityList', ..., 'formitaeten', ..., {dict})):
                for quality in traverse_obj(stream, ('qualities', ..., {dict})):
                    for variant in traverse_obj(quality, ('audio', 'tracks', lambda _, v: url_or_none(v['uri']))):
                        format_url = variant['uri']
                        if format_url in seen_urls:
                            continue
                        seen_urls.add(format_url)
                        ext = determine_ext(format_url)
                        if ext == 'm3u8':
                            fmts = self._extract_m3u8_formats(
                                format_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
                        elif ext in ('mp4', 'webm'):
                            height = int_or_none(quality.get('highestVerticalResolution'))
                            width = round(aspect_ratio * height) if aspect_ratio and height else None
                            fmts = [{
                                'url': format_url,
                                **parse_codecs(quality.get('mimeCodec')),
                                'height': height,
                                'width': width,
                                'filesize': int_or_none(variant.get('filesize')),
                                'format_id': join_nonempty('http', stream.get('type')),
                                'tbr': int_or_none(self._search_regex(r'_(\d+)k_', format_url, 'tbr', default=None)),
                            }]
                        else:
                            self.report_warning(f'Skipping unsupported extension "{ext}"', video_id=video_id)
                            fmts = []

                        f_class = variant.get('class')
                        for f in fmts:
                            f_lang = ISO639Utils.short2long(
                                (f.get('language') or variant.get('language') or '').lower())
                            is_audio_only = f.get('vcodec') == 'none'
                            formats.append({
                                **f,
                                'format_id': join_nonempty(f['format_id'], is_dgs and 'dgs'),
                                'format_note': join_nonempty(
                                    not is_audio_only and f_class,
                                    is_dgs and 'German Sign Language',
                                    f.get('format_note'), delim=', '),
                                'preference': -2 if is_dgs else -1,
                                'language': f_lang,
                                'language_preference': (
                                    -10 if ((is_audio_only and f.get('format_note') == 'Audiodeskription')
                                            or (not is_audio_only and f_class == 'ad'))
                                    else 10 if f_lang == 'deu' and f_class == 'main'
                                    else 5 if f_lang == 'deu'
                                    else 1 if f_class == 'main'
                                    else -1),
                            })

        return {
            'id': content_id or video_id,
            'duration': duration,
            'formats': formats,
            'subtitles': self._extract_subtitles(src_captions),
        }

    def _download_graphql(self, item_id, data_desc, query=None, body=None):
        assert query or body, 'One of query or body is required'

        return self._download_json(
            'https://api.zdf.de/graphql', item_id,
            f'Downloading {data_desc}', f'Failed to download {data_desc}',
            query=query, data=json.dumps(body).encode() if body else None,
            headers=filter_dict({
                'Api-Auth': self._get_api_token(),
                'Apollo-Require-Preflight': True,
                'Content-Type': 'application/json' if body else None,
            }))

    @staticmethod
    def _extract_thumbnails(source):
        return [{
            'id': str(format_id),
            'url': url,
            'preference': 1 if format_id == 'original' else 0,
            **traverse_obj(re.search(r'(?P<width>\d+|auto)[Xx](?P<height>\d+|auto)', str(format_id)), {
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
            }),
        } for format_id, url in traverse_obj(source, ({dict.items}, lambda _, v: url_or_none(v[1])))]


class ZDFIE(ZDFBaseIE):
    _VALID_URL = [
        r'https?://(?:www\.)?zdf\.de/(?:video|play)/(?:[^/?#]+/)*(?P<id>[^/?#]+)',
        # Legacy redirects from before the redesign in 2025-03 or from before sister sites moved to their own domains
        r'https?://(?:www\.)?zdf\.de/(?:[^/?#]+/)*(?P<id>[^/?#]+)\.html',
        # Sister sites
        r'https?://(?:www\.)?(?:zdfheute|logo)\.de/(?:[^/?#]+/)*(?P<id>[^/?#]+)\.html',
    ]
    IE_NAME = 'zdf'
    _TESTS = [{
        # Standalone video (i.e. not part of a playlist), video URL
        'url': 'https://www.zdf.de/video/dokus/sylt---deutschlands-edles-nordlicht-movie-100/sylt-deutschlands-edles-nordlicht-100',
        'info_dict': {
            'id': 'sylt-deutschlands-edles-nordlicht-100',
            'ext': 'mp4',
            'title': 'Sylt - Deutschlands edles Nordlicht',
            'description': 'md5:35407b810c2e1e33efbe15ef6e4c06c3',
            'duration': 810.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/sylt-118~original\?cb=\d+',
            'series': 'Sylt - Deutschlands edles Nordlicht',
            'series_id': 'sylt---deutschlands-edles-nordlicht-movie-100',
            'timestamp': 1612462500,
            'upload_date': '20210204',
            '_old_archive_ids': ['zdf 210402_1915_sendung_dok'],
        },
    }, {
        # Standalone video (i.e. not part of a playlist), play URL
        'url': 'https://www.zdf.de/play/dokus/sylt---deutschlands-edles-nordlicht-movie-100/sylt-deutschlands-edles-nordlicht-100',
        'info_dict': {
            'id': 'sylt-deutschlands-edles-nordlicht-100',
            'ext': 'mp4',
            'title': 'Sylt - Deutschlands edles Nordlicht',
            'description': 'md5:35407b810c2e1e33efbe15ef6e4c06c3',
            'duration': 810.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/sylt-118~original\?cb=\d+',
            'series': 'Sylt - Deutschlands edles Nordlicht',
            'series_id': 'sylt---deutschlands-edles-nordlicht-movie-100',
            'timestamp': 1612462500,
            'upload_date': '20210204',
            '_old_archive_ids': ['zdf 210402_1915_sendung_dok'],
        },
        'params': {'skip_download': True},
    }, {
        # Standalone video (i.e. not part of a playlist), legacy URL before website redesign in 2025-03
        'url': 'https://www.zdf.de/dokumentation/dokumentation-sonstige/sylt-deutschlands-edles-nordlicht-100.html',
        'info_dict': {
            'id': 'sylt-deutschlands-edles-nordlicht-100',
            'ext': 'mp4',
            'title': 'Sylt - Deutschlands edles Nordlicht',
            'description': 'md5:35407b810c2e1e33efbe15ef6e4c06c3',
            'duration': 810.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/sylt-118~original\?cb=\d+',
            'series': 'Sylt - Deutschlands edles Nordlicht',
            'series_id': 'sylt---deutschlands-edles-nordlicht-movie-100',
            'timestamp': 1612462500,
            'upload_date': '20210204',
            '_old_archive_ids': ['zdf 210402_1915_sendung_dok'],
        },
        'params': {'skip_download': True},
    }, {
        # Video belongs to a playlist, video URL
        # Also: video mirrored from ARD Mediathek
        'url': 'https://www.zdf.de/video/dokus/collection-index-page-ard-collection-ard-dxjuomfyzdpzag93ojy2mzhhmmq3mzk2ztq4nda-132/page-video-ard-gelb-vom-hellen-glanz-zu-finsteren-abgruenden-102',
        'md5': '84980c1a0148da6cd94de58333d7e1ee',
        'info_dict': {
            'id': 'page-video-ard-gelb-vom-hellen-glanz-zu-finsteren-abgruenden-102',
            'ext': 'mp4',
            'title': 'Gelb: Vom hellen Glanz zu finsteren Abgründen',
            'description': 'md5:9aad4806b4c8ea152ab21e70c9d516be',
            'duration': 895.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/image-ard-gelb-vom-hellen-glanz-zu-finsteren-abgruenden-102~original\?cb=\d+',
            'series': 'Die Magie der Farben',
            'series_id': 'collection-index-page-ard-collection-ard-dxjuomfyzdpzag93ojy2mzhhmmq3mzk2ztq4nda-132',
            'season': 'Season 2023',
            'season_number': 2023,
            'episode': 'Episode 5',
            'episode_number': 5,
            'timestamp': 1690902120,
            'upload_date': '20230801',
            '_old_archive_ids': ['zdf video_ard_dXJuOmFyZDpwdWJsaWNhdGlvbjo0YTYyOTJjM2Q0ZThlNmY1'],
        },
    }, {
        # Video belongs to a playlist, play URL
        'url': 'https://www.zdf.de/play/dokus/collection-index-page-ard-collection-ard-dxjuomfyzdpzag93ojy2mzhhmmq3mzk2ztq4nda-132/page-video-ard-gelb-vom-hellen-glanz-zu-finsteren-abgruenden-102',
        'info_dict': {
            'id': 'page-video-ard-gelb-vom-hellen-glanz-zu-finsteren-abgruenden-102',
            'ext': 'mp4',
            'title': 'Gelb: Vom hellen Glanz zu finsteren Abgründen',
            'description': 'md5:9aad4806b4c8ea152ab21e70c9d516be',
            'duration': 895.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/image-ard-gelb-vom-hellen-glanz-zu-finsteren-abgruenden-102~original\?cb=\d+',
            'series': 'Die Magie der Farben',
            'series_id': 'collection-index-page-ard-collection-ard-dxjuomfyzdpzag93ojy2mzhhmmq3mzk2ztq4nda-132',
            'season': 'Season 2023',
            'season_number': 2023,
            'episode': 'Episode 5',
            'episode_number': 5,
            'timestamp': 1690902120,
            'upload_date': '20230801',
            '_old_archive_ids': ['zdf video_ard_dXJuOmFyZDpwdWJsaWNhdGlvbjo0YTYyOTJjM2Q0ZThlNmY1'],
        },
        'params': {'skip_download': True},
    }, {
        # Video belongs to a playlist, legacy URL before website redesign in 2025-03
        'url': 'https://www.zdf.de/dokus/collection-index-page-ard-collection-ard-dxjuomfyzdpzag93ojy2mzhhmmq3mzk2ztq4nda-132/page-video-ard-gelb-vom-hellen-glanz-zu-finsteren-abgruenden-102.html',
        'info_dict': {
            'id': 'page-video-ard-gelb-vom-hellen-glanz-zu-finsteren-abgruenden-102',
            'ext': 'mp4',
            'title': 'Gelb: Vom hellen Glanz zu finsteren Abgründen',
            'description': 'md5:9aad4806b4c8ea152ab21e70c9d516be',
            'duration': 895.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/image-ard-gelb-vom-hellen-glanz-zu-finsteren-abgruenden-102~original\?cb=\d+',
            'series': 'Die Magie der Farben',
            'series_id': 'collection-index-page-ard-collection-ard-dxjuomfyzdpzag93ojy2mzhhmmq3mzk2ztq4nda-132',
            'season': 'Season 2023',
            'season_number': 2023,
            'episode': 'Episode 5',
            'episode_number': 5,
            'timestamp': 1690902120,
            'upload_date': '20230801',
            '_old_archive_ids': ['zdf video_ard_dXJuOmFyZDpwdWJsaWNhdGlvbjo0YTYyOTJjM2Q0ZThlNmY1'],
        },
        'params': {'skip_download': True},
    }, {
        # Video with chapters
        # Also: video with sign-language variant
        'url': 'https://www.zdf.de/video/magazine/heute-journal-104/heute-journal-vom-19-12-2021-100',
        'md5': '6ada39465497a84fb98d48ffff69e7b7',
        'info_dict': {
            'id': 'heute-journal-vom-19-12-2021-100',
            'ext': 'mp4',
            'title': 'heute journal vom 19.12.2021',
            'description': 'md5:02504cf3b03777ff32fcc927d260c5dd',
            'duration': 1770.0,
            'thumbnail': 'https://epg-image.zdf.de/fotobase-webdelivery/images/273e5545-16e7-4ca3-898e-52fe9e06d964?layout=1920x1080',
            'chapters': 'count:11',
            'series': 'heute journal',
            'series_id': 'heute-journal-104',
            'season': 'Season 2021',
            'season_number': 2021,
            'episode': 'Episode 370',
            'episode_number': 370,
            'timestamp': 1639946700,
            'upload_date': '20211219',
            # Videos with sign language variants must not have a 'dgs' suffix on their old archive IDs.
            '_old_archive_ids': ['zdf 211219_sendung_hjo'],
        },
    }, {
        # FUNK video (hosted on a different CDN, has atypical PTMD and HLS files)
        'url': 'https://www.zdf.de/video/serien/funk-collection-funk-11790-1596/funk-alles-ist-verzaubert-102',
        'md5': '57af4423db0455a3975d2dc4578536bc',
        'info_dict': {
            'id': 'funk-alles-ist-verzaubert-102',
            'ext': 'mp4',
            'title': 'Alles ist verzaubert',
            'description': 'Die Neue an der Schule verdreht Ismail den Kopf.',
            'duration': 1278.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/teaser-funk-alles-ist-verzaubert-102~original\?cb=\d+',
            'series': 'DRUCK',
            'series_id': 'funk-collection-funk-11790-1596',
            'season': 'Season 2021',
            'season_number': 2021,
            'episode': 'Episode 50',
            'episode_number': 50,
            'timestamp': 1635520560,
            'upload_date': '20211029',
            '_old_archive_ids': ['zdf video_funk_1770473'],
        },
    }, {
        # zdfheute video, also available on zdf.de
        'url': 'https://www.zdfheute.de/video/heute-journal/heute-journal-vom-19-dezember-2025-100.html',
        'md5': '47af8c2cfa30abf74501170f62754c63',
        'info_dict': {
            'id': 'heute-journal-vom-19-dezember-2025-100',
            'ext': 'mp4',
            'title': 'heute journal vom 19. Dezember 2025',
            'description': 'md5:fd0dfbce0783486db839ff9140a8074b',
            'duration': 1780.0,
            'thumbnail': 'https://epg-image.zdf.de/fotobase-webdelivery/images/273e5545-16e7-4ca3-898e-52fe9e06d964?layout=2400x1350',
            'chapters': 'count:10',
            'series': 'heute journal',
            'series_id': 'heute-journal-104',
            'season': 'Season 2025',
            'season_number': 2025,
            'episode': 'Episode 365',
            'episode_number': 365,
            'timestamp': 1766178000,
            'upload_date': '20251219',
            '_old_archive_ids': ['zdf 251219_2200_sendung_hjo'],
        },
    }, {
        # zdfheute video, not available on zdf.de (uses the fallback extraction path)
        'url': 'https://www.zdf.de/nachrichten/politik/deutschland/koalitionsverhandlungen-spd-cdu-csu-dobrindt-100.html',
        'md5': 'c3a78514dd993a5781aa3afe50db51e2',
        'info_dict': {
            'id': 'koalitionsverhandlungen-spd-cdu-csu-dobrindt-100',
            'ext': 'mp4',
            'title': 'Dobrindt schließt Steuererhöhungen aus',
            'description': 'md5:9a117646d7b8df6bc902eb543a9c9023',
            'duration': 325,
            'thumbnail': r're:https://www\.zdfheute\.de/assets/dobrindt-csu-berlin-direkt-100~1920x1080\?cb=\d+',
            'timestamp': 1743374520,
            'upload_date': '20250330',
            '_old_archive_ids': ['zdf 250330_clip_2_bdi'],
        },
    }, {
        # logo! video, also available on zdf.de
        'url': 'https://www.logo.de/logo-vom-freitag-19-dezember-2025-102.html',
        'md5': 'cfb1a0988b1249f052a437a55851134b',
        'info_dict': {
            'id': 'logo-vom-freitag-19-dezember-2025-102',
            'ext': 'mp4',
            'title': 'logo! vom Freitag, 19. Dezember 2025',
            'description': 'md5:971428cb563e924c153580f23870c613',
            'duration': 490.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/iran-rote-erde-sendung-19-dezember-2025-100~original\?cb=\d+',
            'chapters': 'count:7',
            'series': 'logo!',
            'series_id': 'logo-154',
            'season': 'Season 2025',
            'season_number': 2025,
            'episode': 'Episode 382',
            'episode_number': 382,
            'timestamp': 1766168700,
            'upload_date': '20251219',
            '_old_archive_ids': ['zdf 251219_1925_sendung_log'],
        },
    }, {
        # logo! video, not available on zdf.de (uses the fallback extraction path)
        'url': 'https://www.logo.de/kinderreporter-vivaan-trifft-alina-grijseels-100.html',
        'md5': '094cea026babb67aa25fd0108400bc12',
        'info_dict': {
            'id': 'kinderreporter-vivaan-trifft-alina-grijseels-100',
            'ext': 'mp4',
            'title': 'Vivaan trifft Handballerin Alina Grijseels',
            'description': 'md5:9572e7f4340dda823ea4091a76624da6',
            'duration': 166.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/vivaan-alina-grijseels-100~original\?cb=\d+',
            'series': 'logo!',
            'series_id': 'logo-154',
            'timestamp': 1766236320,
            'upload_date': '20251220',
            '_old_archive_ids': ['zdf 251219_kr_alina_grijseels_neu_log'],
        },
    }, {
        # Same as https://www.phoenix.de/sendungen/ereignisse/corona-nachgehakt/wohin-fuehrt-der-protest-in-der-pandemie-a-2050630.html
        'url': 'https://www.zdf.de/politik/phoenix-sendungen/wohin-fuehrt-der-protest-in-der-pandemie-100.html',
        'only_matching': True,
    }, {
        # Same as https://www.3sat.de/film/ab-18/10-wochen-sommer-108.html
        'url': 'https://www.zdf.de/dokumentation/ab-18/10-wochen-sommer-102.html',
        'only_matching': True,
    }, {
        # Same as https://www.phoenix.de/sendungen/dokumentationen/gesten-der-maechtigen-i-a-89468.html?ref=suche
        'url': 'https://www.zdf.de/politik/phoenix-sendungen/die-gesten-der-maechtigen-100.html',
        'only_matching': True,
    }, {
        # Same as https://www.3sat.de/film/spielfilm/der-hauptmann-100.html
        'url': 'https://www.zdf.de/filme/filme-sonstige/der-hauptmann-112.html',
        'only_matching': True,
    }, {
        # Same as https://www.3sat.de/wissen/nano/nano-21-mai-2019-102.html, equal media ids
        'url': 'https://www.zdf.de/wissen/nano/nano-21-mai-2019-102.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/service-und-hilfe/die-neue-zdf-mediathek/zdfmediathek-trailer-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/filme/taunuskrimi/die-lebenden-und-die-toten-1---ein-taunuskrimi-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/dokumentation/planet-e/planet-e-uebersichtsseite-weitere-dokumentationen-von-planet-e-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/arte/todliche-flucht/page-video-artede-toedliche-flucht-16-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/dokumentation/terra-x/unser-gruener-planet-wuesten-doku-100.html',
        'only_matching': True,
    }]

    _GRAPHQL_QUERY = '''
query VideoByCanonical($canonical: String!) {
  videoByCanonical(canonical: $canonical) {
    canonical
    title
    leadParagraph
    editorialDate
    teaser {
      description
      image {
        list
      }
    }
    episodeInfo {
      episodeNumber
      seasonNumber
    }
    smartCollection {
      canonical
      title
    }
    currentMedia {
      nodes {
        ptmdTemplate
        ... on VodMedia {
          duration
          aspectRatio
          streamAnchorTags {
            nodes {
              anchorOffset
              anchorLabel
            }
          }
          vodMediaType
          label
        }
        ... on LiveMedia {
          start
          stop
          encryption
          liveMediaType
          label
        }
        id
      }
    }
  }
}
    '''

    def _extract_ptmd(self, *args, **kwargs):
        ptmd_data = super()._extract_ptmd(*args, **kwargs)
        # This was the video id before the graphql redesign, other extractors still use it as such
        old_archive_id = ptmd_data.pop('id')
        ptmd_data['_old_archive_ids'] = [make_archive_id(self, old_archive_id)]
        return ptmd_data

    # This fallback should generally only happen for pages under `zdf.de/nachrichten`.
    # They are on a separate website for which GraphQL often doesn't return results.
    # The API used here is no longer in use by official clients and likely deprecated.
    # Long-term, news documents probably should use the API used by the mobile apps:
    # https://zdf-prod-futura.zdf.de/news/documents/ (note 'news' vs 'mediathekV2')
    def _extract_fallback(self, document_id):
        video = self._download_json(
            f'https://zdf-prod-futura.zdf.de/mediathekV2/document/{document_id}',
            document_id, note='Downloading fallback metadata',
            errnote='Failed to download fallback metadata')
        document = video['document']

        ptmd_url = traverse_obj(document, (
            ('streamApiUrlAndroid', ('streams', 0, 'streamApiUrlAndroid')),
            {url_or_none}, any, {require('PTMD URL')}))

        thumbnails = []
        for thumbnail_key, thumbnail in traverse_obj(document, ('teaserBild', {dict.items}, ...)):
            thumbnail_url = traverse_obj(thumbnail, ('url', {url_or_none}))
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'id': thumbnail_key,
                'width': int_or_none(thumbnail.get('width')),
                'height': int_or_none(thumbnail.get('height')),
            })

        return {
            'thumbnails': thumbnails,
            **traverse_obj(video, {
                'title': ('document', 'titel', {str}),
                'description': ('document', 'beschreibung', {str}),
                'timestamp': (
                    (('document', 'date'), ('meta', 'editorialDate')),
                    {unified_timestamp}, any),
                'subtitles': ('document', 'captions', {self._extract_subtitles}),
            }),
            **self._extract_ptmd(ptmd_url, document_id, self._get_api_token()),
            'id': document_id,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_graphql(video_id, 'video metadata', body={
            'operationName': 'VideoByCanonical',
            'query': self._GRAPHQL_QUERY,
            'variables': {'canonical': video_id},
        })['data']['videoByCanonical']

        if not video_data:
            return self._extract_fallback(video_id)

        aspect_ratio = None
        ptmd_urls = []
        for node in traverse_obj(video_data, ('currentMedia', 'nodes', lambda _, v: v['ptmdTemplate'])):
            ptmd_url = self._expand_ptmd_template('https://api.zdf.de', node['ptmdTemplate'])
            # Smuggle vod_media_type so that _extract_ptmd is aware of 'DGS' variants
            if vod_media_type := node.get('vodMediaType'):
                ptmd_url = smuggle_url(ptmd_url, {'vod_media_type': vod_media_type})
            ptmd_urls.append(ptmd_url)
            if not aspect_ratio:
                aspect_ratio = self._parse_aspect_ratio(node.get('aspectRatio'))

        return {
            **traverse_obj(video_data, {
                'title': ('title', {str}),
                'description': (('leadParagraph', ('teaser', 'description')), any, {str}),
                'timestamp': ('editorialDate', {parse_iso8601}),
                'thumbnails': ('teaser', 'image', 'list', {self._extract_thumbnails}),
                'episode_number': ('episodeInfo', 'episodeNumber', {int_or_none}),
                'season_number': ('episodeInfo', 'seasonNumber', {int_or_none}),
                'series': ('smartCollection', 'title', {str}),
                'series_id': ('smartCollection', 'canonical', {str}),
                'chapters': ('currentMedia', 'nodes', 0, 'streamAnchorTags', 'nodes', {self._extract_chapters}),
            }),
            **self._extract_ptmd(ptmd_urls, video_id, self._get_api_token(), aspect_ratio),
            'id': video_id,
        }


class ZDFChannelIE(ZDFBaseIE):
    _VALID_URL = r'https?://www\.zdf\.de/(?:[^/?#]+/)*(?P<id>[^/?#]+)'
    IE_NAME = 'zdf:channel'
    _TESTS = [{
        # Playlist, legacy URL before website redesign in 2025-03
        'url': 'https://www.zdf.de/sport/das-aktuelle-sportstudio',
        'info_dict': {
            'id': 'das-aktuelle-sportstudio-220',
            'title': 'das aktuelle sportstudio',
            'description': 'md5:e46c785324238a03edcf8b301c5fd5dc',
        },
        'playlist_mincount': 25,
    }, {
        # Playlist, current URL
        'url': 'https://www.zdf.de/sport/das-aktuelle-sportstudio-220',
        'info_dict': {
            'id': 'das-aktuelle-sportstudio-220',
            'title': 'das aktuelle sportstudio',
            'description': 'md5:e46c785324238a03edcf8b301c5fd5dc',
        },
        'playlist_mincount': 25,
    }, {
        # Standalone video (i.e. not part of a playlist), collection URL
        'add_ie': [ZDFIE.ie_key()],
        'url': 'https://www.zdf.de/dokus/sylt---deutschlands-edles-nordlicht-movie-100',
        'info_dict': {
            'id': 'sylt-deutschlands-edles-nordlicht-100',
            'ext': 'mp4',
            'title': 'Sylt - Deutschlands edles Nordlicht',
            'description': 'md5:35407b810c2e1e33efbe15ef6e4c06c3',
            'duration': 810.0,
            'thumbnail': r're:https://www\.zdf\.de/assets/sylt-118~original\?cb=\d+',
            'series': 'Sylt - Deutschlands edles Nordlicht',
            'series_id': 'sylt---deutschlands-edles-nordlicht-movie-100',
            'timestamp': 1612462500,
            'upload_date': '20210204',
            '_old_archive_ids': ['zdf 210402_1915_sendung_dok'],
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.zdf.de/gesellschaft/aktenzeichen-xy-ungeloest',
        'info_dict': {
            'id': 'aktenzeichen-xy-ungeloest-110',
            'title': 'Aktenzeichen XY... Ungelöst',
            'description': 'md5:b79ac0d64b979e53cbe510c0ca9cb7be',
        },
        'playlist_mincount': 2,
    }, {
        # All seasons of playlist
        'url': 'https://www.zdf.de/magazine/heute-journal-104',
        'info_dict': {
            'id': 'heute-journal-104',
            'title': 'heute journal',
            'description': 'md5:6edad39189abf8431795d3d6d7f986b3',
        },
        'playlist_mincount': 366,
    }, {
        # Only selected season
        'url': 'https://www.zdf.de/magazine/heute-journal-104?staffel=2025',
        'info_dict': {
            'id': 'heute-journal-104-s2025',
            'title': 'heute journal - Season 2025',
            'description': 'md5:6edad39189abf8431795d3d6d7f986b3',
        },
        'playlist_mincount': 1,
        'playlist_maxcount': 365,
    }]

    _PAGE_SIZE = 24

    @classmethod
    def suitable(cls, url):
        return False if ZDFIE.suitable(url) else super().suitable(url)

    def _fetch_page(self, playlist_id, canonical_id, season_idx, season_number, page_number, cursor=None):
        return self._download_graphql(
            playlist_id, f'season {season_number} page {page_number} JSON', query={
                'operationName': 'seasonByCanonical',
                'variables': json.dumps(filter_dict({
                    'seasonIndex': season_idx,
                    'canonical': canonical_id,
                    'episodesPageSize': self._PAGE_SIZE,
                    'episodesAfter': cursor,
                })),
                'extensions': json.dumps({
                    'persistedQuery': {
                        'version': 1,
                        'sha256Hash': '9412a0f4ac55dc37d46975d461ec64bfd14380d815df843a1492348f77b5c99a',
                    },
                }),
            })['data']['smartCollectionByCanonical']

    def _entries(self, playlist_id, canonical_id, season_numbers, requested_season_number):
        for season_idx, season_number in enumerate(season_numbers):
            if requested_season_number is not None and requested_season_number != season_number:
                continue

            cursor = None
            for page_number in itertools.count(1):
                page = self._fetch_page(
                    playlist_id, canonical_id, season_idx, season_number, page_number, cursor)

                nodes = traverse_obj(page, ('seasons', 'nodes', ...))

                for episode in traverse_obj(nodes, (
                    ..., 'episodes', 'nodes', lambda _, v: url_or_none(v['sharingUrl']),
                )):
                    yield self.url_result(
                        episode['sharingUrl'], ZDFIE,
                        **traverse_obj(episode, {
                            'id': ('canonical', {str}),
                            'title': ('teaser', 'title', {str}),
                            'description': (('leadParagraph', ('teaser', 'description')), any, {str}),
                            'timestamp': ('editorialDate', {parse_iso8601}),
                            'episode_number': ('episodeInfo', 'episodeNumber', {int_or_none}),
                            'season_number': ('episodeInfo', 'seasonNumber', {int_or_none}),
                        }))

                page_info = traverse_obj(nodes, (-1, 'episodes', 'pageInfo', {dict})) or {}
                if not page_info.get('hasNextPage') or not page_info.get('endCursor'):
                    break
                cursor = page_info['endCursor']

    def _real_extract(self, url):
        canonical_id = self._match_id(url)
        # Make sure to get the correct ID in case of redirects
        urlh = self._request_webpage(url, canonical_id)
        canonical_id = self._search_regex(self._VALID_URL, urlh.url, 'channel id', group='id')
        season_number = traverse_obj(parse_qs(url), ('staffel', -1, {int_or_none}))
        playlist_id = join_nonempty(canonical_id, season_number and f's{season_number}')

        collection_data = self._download_graphql(
            playlist_id, 'smart collection data', query={
                'operationName': 'GetSmartCollectionByCanonical',
                'variables': json.dumps({
                    'canonical': canonical_id,
                    'videoPageSize': 100,  # Use max page size to get episodes from all seasons
                }),
                'extensions': json.dumps({
                    'persistedQuery': {
                        'version': 1,
                        'sha256Hash': 'cb49420e133bd668ad895a8cea0e65cba6aa11ac1cacb02341ff5cf32a17cd02',
                    },
                }),
            })['data']['smartCollectionByCanonical']
        video_data = traverse_obj(collection_data, ('video', {dict})) or {}
        season_numbers = traverse_obj(collection_data, ('seasons', 'seasons', ..., 'number', {int_or_none}))

        if not self._yes_playlist(
            season_numbers and playlist_id,
            url_or_none(video_data.get('sharingUrl')) and video_data.get('canonical'),
        ):
            return self.url_result(video_data['sharingUrl'], ZDFIE, video_data['canonical'])

        if season_number is not None and season_number not in season_numbers:
            raise ExtractorError(f'Season {season_number} was not found in the collection data')

        return self.playlist_result(
            self._entries(playlist_id, canonical_id, season_numbers, season_number),
            playlist_id, join_nonempty(
                traverse_obj(collection_data, ('title', {str})),
                season_number and f'Season {season_number}', delim=' - '),
            traverse_obj(collection_data, ('infoText', {str})))
