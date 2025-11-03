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
        # /nachrichten/ sub-site URLs and legacy redirects from before the redesign in 2025-03
        r'https?://(?:www\.)?zdf\.de/(?:[^/?#]+/)*(?P<id>[^/?#]+)\.html',
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
            'thumbnail': 'https://www.zdf.de/assets/sylt-118~original?cb=1613992485011',
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
            'thumbnail': 'https://www.zdf.de/assets/sylt-118~original?cb=1613992485011',
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
            'thumbnail': 'https://www.zdf.de/assets/sylt-118~original?cb=1613992485011',
            'series': 'Sylt - Deutschlands edles Nordlicht',
            'series_id': 'sylt---deutschlands-edles-nordlicht-movie-100',
            'timestamp': 1612462500,
            'upload_date': '20210204',
            '_old_archive_ids': ['zdf 210402_1915_sendung_dok'],
        },
        'params': {'skip_download': True},
    }, {
        # Video belongs to a playlist, video URL
        'url': 'https://www.zdf.de/video/dokus/die-magie-der-farben-116/die-magie-der-farben-von-koenigspurpur-und-jeansblau-100',
        'md5': '1eda17eb40a9ead3046326e10b9c5973',
        'info_dict': {
            'id': 'die-magie-der-farben-von-koenigspurpur-und-jeansblau-100',
            'ext': 'mp4',
            'title': 'Von Königspurpur bis Jeansblau',
            'description': 'md5:a89da10c928c6235401066b60a6d5c1a',
            'duration': 2615.0,
            'thumbnail': 'https://www.zdf.de/assets/koenigspurpur-bis-jeansblau-100~original?cb=1741857765971',
            'series': 'Die Magie der Farben',
            'series_id': 'die-magie-der-farben-116',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 1445797800,
            'upload_date': '20151025',
            '_old_archive_ids': ['zdf 151025_magie_farben2_tex'],
        },
    }, {
        # Video belongs to a playlist, play URL
        'url': 'https://www.zdf.de/play/dokus/die-magie-der-farben-116/die-magie-der-farben-von-koenigspurpur-und-jeansblau-100',
        'md5': '1eda17eb40a9ead3046326e10b9c5973',
        'info_dict': {
            'id': 'die-magie-der-farben-von-koenigspurpur-und-jeansblau-100',
            'ext': 'mp4',
            'title': 'Von Königspurpur bis Jeansblau',
            'description': 'md5:a89da10c928c6235401066b60a6d5c1a',
            'duration': 2615.0,
            'thumbnail': 'https://www.zdf.de/assets/koenigspurpur-bis-jeansblau-100~original?cb=1741857765971',
            'series': 'Die Magie der Farben',
            'series_id': 'die-magie-der-farben-116',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 1445797800,
            'upload_date': '20151025',
            '_old_archive_ids': ['zdf 151025_magie_farben2_tex'],
        },
        'params': {'skip_download': True},
    }, {
        # Video belongs to a playlist, legacy URL before website redesign in 2025-03
        'url': 'https://www.zdf.de/dokumentation/terra-x/die-magie-der-farben-von-koenigspurpur-und-jeansblau-100.html',
        'md5': '1eda17eb40a9ead3046326e10b9c5973',
        'info_dict': {
            'id': 'die-magie-der-farben-von-koenigspurpur-und-jeansblau-100',
            'ext': 'mp4',
            'title': 'Von Königspurpur bis Jeansblau',
            'description': 'md5:a89da10c928c6235401066b60a6d5c1a',
            'duration': 2615.0,
            'thumbnail': 'https://www.zdf.de/assets/koenigspurpur-bis-jeansblau-100~original?cb=1741857765971',
            'series': 'Die Magie der Farben',
            'series_id': 'die-magie-der-farben-116',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 1445797800,
            'upload_date': '20151025',
            '_old_archive_ids': ['zdf 151025_magie_farben2_tex'],
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
        # Video that requires fallback extraction
        'url': 'https://www.zdf.de/nachrichten/politik/deutschland/koalitionsverhandlungen-spd-cdu-csu-dobrindt-100.html',
        'md5': 'c3a78514dd993a5781aa3afe50db51e2',
        'info_dict': {
            'id': 'koalitionsverhandlungen-spd-cdu-csu-dobrindt-100',
            'ext': 'mp4',
            'title': 'Dobrindt schließt Steuererhöhungen aus',
            'description': 'md5:9a117646d7b8df6bc902eb543a9c9023',
            'duration': 325,
            'thumbnail': 'https://www.zdfheute.de/assets/dobrindt-csu-berlin-direkt-100~1920x1080?cb=1743357653736',
            'timestamp': 1743374520,
            'upload_date': '20250330',
            '_old_archive_ids': ['zdf 250330_clip_2_bdi'],
        },
    }, {
        # FUNK video (hosted on a different CDN, has atypical PTMD and HLS files)
        'url': 'https://www.zdf.de/funk/druck-11790/funk-alles-ist-verzaubert-102.html',
        'md5': '57af4423db0455a3975d2dc4578536bc',
        'info_dict': {
            'id': 'funk-alles-ist-verzaubert-102',
            'ext': 'mp4',
            'title': 'Alles ist verzaubert',
            'description': 'Die Neue an der Schule verdreht Ismail den Kopf.',
            'duration': 1278.0,
            'thumbnail': 'https://www.zdf.de/assets/teaser-funk-alles-ist-verzaubert-102~original?cb=1663848412907',
            'series': 'DRUCK',
            'series_id': 'funk-collection-funk-11790-1590',
            'season': 'Season 7',
            'season_number': 7,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1635520560,
            'upload_date': '20211029',
            '_old_archive_ids': ['zdf video_funk_1770473'],
        },
    }, {
        'url': 'https://www.zdf.de/serien/soko-stuttgart/das-geld-anderer-leute-100.html',
        'info_dict': {
            'id': 'das-geld-anderer-leute-100',
            'ext': 'mp4',
            'title': 'Das Geld anderer Leute',
            'description': 'md5:cb6f660850dc5eb7d1ab776ea094959d',
            'duration': 2581.0,
            'thumbnail': 'https://epg-image.zdf.de/fotobase-webdelivery/images/e2d7e55a-09f0-424e-ac73-6cac4dd65f35?layout=1920x1080',
            'series': 'SOKO Stuttgart',
            'series_id': 'soko-stuttgart-104',
            'season': 'Season 11',
            'season_number': 11,
            'episode': 'Episode 10',
            'episode_number': 10,
            'timestamp': 1728983700,
            'upload_date': '20241015',
            '_old_archive_ids': ['zdf 191205_1800_sendung_sok8'],
        },
    }, {
        'url': 'https://www.zdf.de/serien/northern-lights/begegnung-auf-der-bruecke-100.html',
        'info_dict': {
            'id': 'begegnung-auf-der-bruecke-100',
            'ext': 'webm',
            'title': 'Begegnung auf der Brücke',
            'description': 'md5:e53a555da87447f7f1207f10353f8e45',
            'duration': 3083.0,
            'thumbnail': 'https://epg-image.zdf.de/fotobase-webdelivery/images/c5ff1d1f-f5c8-4468-86ac-1b2f1dbecc76?layout=1920x1080',
            'series': 'Northern Lights',
            'series_id': 'northern-lights-100',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1738546500,
            'upload_date': '20250203',
            '_old_archive_ids': ['zdf 240319_2310_sendung_not'],
        },
        'params': {'skip_download': 'geo-restricted http format'},
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
            'thumbnail': 'https://www.zdf.de/assets/sylt-118~original?cb=1613992485011',
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
        'url': 'https://www.zdf.de/serien/taunuskrimi/',
        'info_dict': {
            'id': 'taunuskrimi-100',
            'title': 'Taunuskrimi',
            'description': 'md5:ee7204e9c625c3b611d1274f9d0e3070',
        },
        'playlist_mincount': 8,
    }, {
        'url': 'https://www.zdf.de/serien/taunuskrimi/?staffel=1',
        'info_dict': {
            'id': 'taunuskrimi-100-s1',
            'title': 'Taunuskrimi - Season 1',
            'description': 'md5:ee7204e9c625c3b611d1274f9d0e3070',
        },
        'playlist_count': 7,
    }, {
        'url': 'https://www.zdf.de/magazine/heute-journal-104',
        'info_dict': {
            'id': 'heute-journal-104',
            'title': 'heute journal',
            'description': 'md5:6edad39189abf8431795d3d6d7f986b3',
        },
        'playlist_mincount': 500,
    }, {
        'url': 'https://www.zdf.de/magazine/heute-journal-104?staffel=2024',
        'info_dict': {
            'id': 'heute-journal-104-s2024',
            'title': 'heute journal - Season 2024',
            'description': 'md5:6edad39189abf8431795d3d6d7f986b3',
        },
        'playlist_count': 242,
        'skip': 'Video count changes daily, needs support for playlist_maxcount',
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
