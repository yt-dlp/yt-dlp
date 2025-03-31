import json
import re
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    merge_dicts,
    parse_codecs,
    parse_iso8601,
    parse_qs,
    qualities,
    traverse_obj,
    try_get,
    unified_timestamp,
    update_url_query,
    url_or_none,
    urljoin,
    variadic,
)


class ZDFBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['DE']
    _QUALITIES = ('auto', 'low', 'med', 'high', 'veryhigh', 'hd', 'fhd', 'uhd')

    def _call_api(self, url, video_id, item, api_token=None):
        headers = {'Api-Auth': api_token} if api_token else {}
        return self._download_json(
            url, video_id, note=f'Downloading {item}',
            errnote=f'Failed to download {item}', headers=headers)

    def _extract_chapters(self, data):
        return traverse_obj(data, (lambda _, v: 'anchorOffset' in v, {
            'start_time': ('anchorOffset', {float_or_none}),
            'title': ('anchorLabel', {str}),
        }), default=None)

    @staticmethod
    def _extract_subtitles(src):
        seen_urls = set()
        subtitles = {}
        for caption in src:
            subtitle_url = url_or_none(caption.get('uri'))
            if not subtitle_url or subtitle_url in seen_urls:
                continue
            seen_urls.add(subtitle_url)
            lang = caption.get('language', 'deu')
            subtitles.setdefault(lang, []).append({
                'url': subtitle_url,
            })
        return subtitles

    def _extract_format(self, video_id, formats, format_urls, meta):
        format_url = url_or_none(meta.get('url'))
        if not format_url or format_url in format_urls:
            return
        format_urls.add(format_url)

        mime_type, ext = meta.get('mimeType'), determine_ext(format_url)
        if mime_type == 'application/x-mpegURL' or ext == 'm3u8':
            new_formats = self._extract_m3u8_formats(
                format_url, video_id, 'mp4', m3u8_id='hls',
                entry_protocol='m3u8_native', fatal=False)
        elif mime_type == 'application/f4m+xml' or ext == 'f4m':
            new_formats = self._extract_f4m_formats(
                update_url_query(format_url, {'hdcore': '3.7.0'}), video_id, f4m_id='hds', fatal=False)
        elif ext == 'mpd':
            new_formats = self._extract_mpd_formats(
                format_url, video_id, mpd_id='dash', fatal=False)
        else:
            f = parse_codecs(meta.get('mimeCodec'))
            if not f and meta.get('type'):
                data = meta['type'].split('_')
                if try_get(data, lambda x: x[2]) == ext:
                    f = {'vcodec': data[0], 'acodec': data[1]}
            f.update({
                'url': format_url,
                'format_id': join_nonempty('http', meta.get('type'), meta.get('quality')),
                'tbr': int_or_none(self._search_regex(r'_(\d+)k_', format_url, 'tbr', default=None)),
            })
            new_formats = [f]
        formats.extend(merge_dicts(f, {
            'format_note': join_nonempty('quality', 'class', from_dict=meta, delim=', '),
            'language': meta.get('language'),
            'language_preference': 10 if meta.get('class') == 'main' else -10 if meta.get('class') == 'ad' else -1,
            'quality': qualities(self._QUALITIES)(meta.get('quality')),
        }) for f in new_formats)

    def _extract_ptmd(self, api_base_url, templates, video_id, api_token=None):
        # TODO: HTTPS formats are extracted without resolution information
        # However, we know vertical resolution and the caller often knows apsect ratio.
        # So we could calculate the correct resulution from those two data points.
        templates = variadic(templates)
        src_captions = []

        content_id = None
        duration = None
        formats = []
        track_uris = set()
        for template in templates:
            ptmd_url = urljoin(api_base_url, template.replace(
                '{playerId}', 'android_native_6'))
            ptmd = self._call_api(ptmd_url, video_id, 'PTMD data', api_token)
            content_id = content_id or ptmd.get('basename') or ptmd_url.split('/')[-1]
            duration = (duration or float_or_none(try_get(
                ptmd, lambda x: x['attributes']['duration']['value']), scale=1000))
            src_captions += ptmd.get('captions') or []
            for p in ptmd['priorityList']:
                formitaeten = p.get('formitaeten')
                if not isinstance(formitaeten, list):
                    continue
                for f in formitaeten:
                    f_qualities = f.get('qualities')
                    if not isinstance(f_qualities, list):
                        continue
                    for quality in f_qualities:
                        tracks = try_get(quality, lambda x: x['audio']['tracks'], list)
                        if not tracks:
                            continue
                        for track in tracks:
                            self._extract_format(
                                content_id, formats, track_uris, {
                                    'url': track.get('uri'),
                                    'type': f.get('type'),
                                    'mimeType': f.get('mimeType'),
                                    'quality': quality.get('quality'),
                                    'class': track.get('class'),
                                    'language': track.get('language'),
                                })

        return {
            'extractor_key': ZDFIE.ie_key(),
            'id': content_id,
            'duration': duration,
            'formats': formats,
            'subtitles': self._extract_subtitles(src_captions),
            '_format_sort_fields': ('tbr', 'res', 'quality', 'language_preference'),
        }

    def _get_api_token(self, video_id):
        # As of 2025-03, this API is used by the Android app for getting tokens.
        # An equivalent token could be extracted from the webpage should the API become unavailable.
        # For now this allows the extractor to avoid dealing with Next.js hydration data.
        TOKEN_CACHE_SECTION = 'zdf'
        TOKEN_CACHE_KEY = 'api-token'
        token_data = self.cache.load(TOKEN_CACHE_SECTION, TOKEN_CACHE_KEY)
        if traverse_obj(token_data, ('expires', {int_or_none}), default=0) < int(time.time()):
            token_data = self._download_json(
                'https://zdf-prod-futura.zdf.de/mediathekV2/token', video_id,
                note='Downloading API token')
            self.cache.store(TOKEN_CACHE_SECTION, TOKEN_CACHE_KEY, token_data)
        return f'{token_data["type"]} {token_data["token"]}'

    def _download_graphql(self, item_id, data_desc, query=None, body=None):
        if not query and not body:
            raise ExtractorError(
                'GraphQL API requires either query parameters or a body',
                video_id=item_id)

        return self._download_json(
            'https://api.zdf.de/graphql', item_id, note=f'Downloading {data_desc}',
            errnote=f'Failed to download {data_desc}', query=query,
            data=json.dumps(body).encode() if body else None, headers={
                'Api-Auth': self._get_api_token(item_id),
                'Apollo-Require-Preflight': True,
                'Content-Type': 'application/json' if body else None,
            })

    @staticmethod
    def _extract_thumbnails(source):
        return [{
            'id': format_id,
            'url': url,
            'preference': 1 if format_id == 'original' else 0,
            **traverse_obj(re.search(r'(?P<width>\d+|auto)[Xx](?P<height>\d+|auto)', format_id), {
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
            }),
        } for format_id, url in (source or {}).items() if url]


class ZDFIE(ZDFBaseIE):
    _VALID_URL = [
        # Legacy URLs end in .html and redirect
        r'https?://(?:www\.)?zdf\.de/(?:[^/?#]+/)*(?P<id>[^/?#]+)\.html',
        r'https?://(?:www\.)?zdf\.de/(?:video|play)/(?:[^/?#]+/)*(?P<id>[^/?#]+)/?',
    ]
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
            '_old_archive_ids': ['210402_1915_sendung_dok'],
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
            '_old_archive_ids': ['210402_1915_sendung_dok'],
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
            '_old_archive_ids': ['210402_1915_sendung_dok'],
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
            '_old_archive_ids': ['151025_magie_farben2_tex'],
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
            '_old_archive_ids': ['151025_magie_farben2_tex'],
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
            '_old_archive_ids': ['151025_magie_farben2_tex'],
        },
        'params': {'skip_download': True},
    }, {
        # Video with chapters
        'url': 'https://www.zdf.de/video/magazine/heute-journal-104/heute-journal-vom-19-12-2021-100',
        'md5': '1175003f28507bd27b266181c4de9f56',
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
            '_old_archive_ids': ['211219_sendung_hjo_dgs'],
        },
    }, {
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
            '_old_archive_ids': ['video_funk_1770473'],
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
            '_old_archive_ids': ['191205_1800_sendung_sok8'],
        },
    }, {
        'url': 'https://www.zdf.de/serien/northern-lights/begegnung-auf-der-bruecke-100.html',
        'info_dict': {
            'id': 'begegnung-auf-der-bruecke-100',
            'ext': 'mp4',
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
            '_old_archive_ids': ['240319_2310_sendung_not'],
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

    @classmethod
    def suitable(cls, url):
        return False if ZDFHeuteIE.suitable(url) else super().suitable(url)

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

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_graphql(video_id, 'video metadata', body={
            'operationName': 'VideoByCanonical',
            'query': self._GRAPHQL_QUERY,
            'variables': {'canonical': video_id},
        })
        # TODO: If there are multiple PTMD templates,
        # usually one of them is a sign-language variant of the video.
        # The format order works out fine as is and prefers the "normal" video,
        # but this should probably be made more explicit.
        ptmd_templates = traverse_obj(
            video_data,
            ('data', 'videoByCanonical', 'currentMedia', 'nodes', ..., 'ptmdTemplate'))
        ptmd_data = self._extract_ptmd(
            'https://api.zdf.de', ptmd_templates, video_id,
            self._get_api_token(video_id))
        # We can't use the ID from PTMD extraction as the video ID
        # because it is not available during playlist extraction.
        # We fix it here manually instead of inside the method
        # because other extractors do rely on using it as their ID.
        ptmd_data['_old_archive_ids'] = [ptmd_data['id']]
        del ptmd_data['id']

        return {
            'id': video_id,
            **ptmd_data,
            **traverse_obj(video_data, ('data', 'videoByCanonical', {
                'title': ('title', {str}),
                'description': (('leadParagraph', ('teaser', 'description')), any, {str}),
                'timestamp': ('editorialDate', {parse_iso8601}),
                'thumbnails': ('teaser', 'image', 'list', {self._extract_thumbnails}),
                'episode_number': ('episodeInfo', 'episodeNumber', {int_or_none}),
                'season_number': ('episodeInfo', 'seasonNumber', {int_or_none}),
                'series': ('smartCollection', 'title', {str}),
                'series_id': ('smartCollection', 'canonical', {str}),
                'chapters': ('currentMedia', 'nodes', 0, 'streamAnchorTags', 'nodes', {self._extract_chapters}),
            })),
        }


class ZDFChannelIE(ZDFBaseIE):
    _VALID_URL = r'https?://www\.zdf\.de/(?:[^/?#]+/)*(?P<id>[^/?#]+)'
    _TESTS = [{
        # Playlist, legacy URL before website redesign in 2025-03
        'url': 'https://www.zdf.de/sport/das-aktuelle-sportstudio',
        'info_dict': {
            'id': 'das-aktuelle-sportstudio-220',
            'title': 'das aktuelle sportstudio',
            'description': 'md5:e46c785324238a03edcf8b301c5fd5dc',
        },
        'playlist_mincount': 18,
    }, {
        # Playlist, current URL
        'url': 'https://www.zdf.de/sport/das-aktuelle-sportstudio-220',
        'info_dict': {
            'id': 'das-aktuelle-sportstudio-220',
            'title': 'das aktuelle sportstudio',
            'description': 'md5:e46c785324238a03edcf8b301c5fd5dc',
        },
        'playlist_mincount': 18,
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
            '_old_archive_ids': ['210402_1915_sendung_dok'],
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
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if ZDFIE.suitable(url) or ZDFHeuteIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, channel_id)
        # Make sure to get the correct ID in case of redirects
        channel_id = self._search_regex(self._VALID_URL, urlh.url, 'channel id', group='id')

        collection_data = self._download_graphql(
            channel_id, 'smart collection data', query={
                'operationName': 'GetSmartCollectionByCanonical',
                'variables': json.dumps({
                    'canonical': channel_id,
                    'videoPageSize': 100,
                }),
                'extensions': json.dumps({
                    'persistedQuery': {
                        'version': 1,
                        'sha256Hash': 'cb49420e133bd668ad895a8cea0e65cba6aa11ac1cacb02341ff5cf32a17cd02',
                    },
                }),
            })

        video_data = traverse_obj(
            collection_data, ('data', 'smartCollectionByCanonical', 'video'))
        season_data = traverse_obj(
            collection_data, ('data', 'smartCollectionByCanonical', 'seasons'))

        if not self._yes_playlist(
                channel_id if season_data else None,
                traverse_obj(video_data, ('canonical', {str}))):
            return self.url_result(video_data['sharingUrl'], ie=ZDFIE)

        title = (traverse_obj(collection_data, ('data', 'smartCollectionByCanonical', 'title'))
                 or self._html_search_meta(
            ['og:title', 'title', 'twitter:title'], webpage, 'title', fatal=False))

        needs_pagination = traverse_obj(season_data, (
            'seasons', ..., 'episodes', 'pageInfo', 'hasNextPage',
            lambda _, v: v is True, any), default=False)
        if needs_pagination:
            # TODO: Implement pagination for collections with long seasons
            # e.g. https://www.zdf.de/magazine/heute-journal-104
            self.report_warning('This collections contains seasons with more than 100 episodes, some episodes are missing from the result.')

        videos = traverse_obj(season_data, ('seasons', ..., 'episodes', 'videos', ...))
        season_id = parse_qs(url).get('staffel', [None])[-1]
        videos = [v for v in videos
                  if not season_id or season_id == str(traverse_obj(v, ('episodeInfo', 'seasonNumber')))]
        entries = [self.url_result(video['sharingUrl'], ZDFIE, **traverse_obj(video, {
            'id': ('canonical', {str}),
            'title': ('teaser', 'title', {str}),
            'description': (('leadParagraph', ('teaser', 'description')), any, {str}),
            'timestamp': ('editorialDate', {parse_iso8601}),
            'thumbnails': ('teaser', 'imageWithoutLogo', 'layouts', {self._extract_thumbnails}),
            'episode_number': ('episodeInfo', 'episodeNumber', {int_or_none}),
            'season_number': ('episodeInfo', 'seasonNumber', {int_or_none}),
            'series_id': {lambda _: channel_id},
            'series': {lambda _: title},
        })) for video in videos or [] if video.get('currentMediaType') != 'NOVIDEO']

        return self.playlist_result(entries, channel_id, title, traverse_obj(
            collection_data, ('data', 'smartCollectionByCanonical', 'infoText', {str})))


# TODO: This extractor is a minimal effort implementation and incomplete.
# It only does what is necessary to get back the functionality that was present
# before the redesign of the ZDF website in 2025-03.
# It uses an API that is no longer used by offical clients,
# and likely never was at all for the purpase the extractor uses it for.
# A proper implementation should likely use the API of the mobile app instead:
# https://zdf-prod-futura.zdf.de/news/documents/ (note 'news' vs 'mediathekV2')
class ZDFHeuteIE(ZDFBaseIE):
    _VALID_URL = r'https?://(?:www\.)?zdf\.de/nachrichten/(?:[^/?#]+/)*(?P<id>[^/?#]+)\.html'
    _TESTS = [{
        'url': 'https://www.zdf.de/nachrichten/zdfheute-live/beckenbauer-gedenkfeier-muenchen-video-100.html',
        'md5': 'd28621e4cd8bcdc25fdefdf12dc79a1e',
        'info_dict': {
            'id': '240119_beckenbauer_gesamt_hli',
            'ext': 'mp4',
            'title': 'Gedenkfeier für Franz Beckenbauer',
            'description': 'md5:a50f2ee818d4a78f20179b88affbe9da',
            'duration': 6510,
            'thumbnail': 'https://www.zdf.de/assets/beckenbauer-trauerfeier-muenchen-tn-102~1920x1080?cb=1705669625816',
            'timestamp': 1705674600,
            'upload_date': '20240119',
        },
    }]

    def _download_v2_doc(self, document_id):
        return self._download_json(
            f'https://zdf-prod-futura.zdf.de/mediathekV2/document/{document_id}',
            document_id)

    def _extract_mobile(self, video_id):
        video = self._download_v2_doc(video_id)

        formats = []
        formitaeten = try_get(video, lambda x: x['document']['formitaeten'], list)
        document = formitaeten and video['document']
        if formitaeten:
            title = document['titel']
            content_id = document['basename']

            format_urls = set()
            for f in formitaeten or []:
                self._extract_format(content_id, formats, format_urls, f)

        thumbnails = []
        teaser_bild = document.get('teaserBild')
        if isinstance(teaser_bild, dict):
            for thumbnail_key, thumbnail in teaser_bild.items():
                thumbnail_url = try_get(
                    thumbnail, lambda x: x['url'], str)
                if thumbnail_url:
                    thumbnails.append({
                        'url': thumbnail_url,
                        'id': thumbnail_key,
                        'width': int_or_none(thumbnail.get('width')),
                        'height': int_or_none(thumbnail.get('height')),
                    })

        return {
            'id': content_id,
            'title': title,
            'description': document.get('beschreibung'),
            'duration': int_or_none(document.get('length')),
            'timestamp': unified_timestamp(document.get('date')) or unified_timestamp(
                try_get(video, lambda x: x['meta']['editorialDate'], str)),
            'thumbnails': thumbnails,
            'subtitles': self._extract_subtitles(document.get('captions') or []),
            'formats': formats,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._extract_mobile(video_id)
