import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    filter_dict,
    find_xpath_attr,
    fix_xml_ampersands,
    GeoRestrictedError,
    HEADRequest,
    int_or_none,
    join_nonempty,
    parse_duration,
    remove_start,
    strip_or_none,
    traverse_obj,
    try_get,
    unified_strdate,
    unified_timestamp,
    update_url_query,
    urljoin,
    xpath_text,
)


class RaiBaseIE(InfoExtractor):
    _UUID_RE = r'[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}'
    _GEO_COUNTRIES = ['IT']
    _GEO_BYPASS = False

    def _extract_relinker_info(self, relinker_url, video_id, audio_only=False):
        if not re.match(r'https?://', relinker_url):
            return {'formats': [{'url': relinker_url}]}

        formats = []
        geoprotection = None
        is_live = None
        duration = None

        for platform in ('mon', 'flash', 'native'):
            relinker = self._download_xml(
                relinker_url, video_id,
                note='Downloading XML metadata for platform %s' % platform,
                transform_source=fix_xml_ampersands,
                query={'output': 45, 'pl': platform},
                headers=self.geo_verification_headers())

            if not geoprotection:
                geoprotection = xpath_text(
                    relinker, './geoprotection', default=None) == 'Y'

            if not is_live:
                is_live = xpath_text(
                    relinker, './is_live', default=None) == 'Y'
            if not duration:
                duration = parse_duration(xpath_text(
                    relinker, './duration', default=None))

            url_elem = find_xpath_attr(relinker, './url', 'type', 'content')
            if url_elem is None:
                continue

            media_url = url_elem.text

            # This does not imply geo restriction (e.g.
            # http://www.raisport.rai.it/dl/raiSport/media/rassegna-stampa-04a9f4bd-b563-40cf-82a6-aad3529cb4a9.html)
            if '/video_no_available.mp4' in media_url:
                continue

            ext = determine_ext(media_url)
            if (ext == 'm3u8' and platform != 'mon') or (ext == 'f4m' and platform != 'flash'):
                continue

            if ext == 'mp3':
                formats.append({
                    'url': media_url,
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'format_id': 'http-mp3',
                })
                break
            elif ext == 'm3u8' or 'format=m3u8' in media_url or platform == 'mon':
                formats.extend(self._extract_m3u8_formats(
                    media_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            elif ext == 'f4m' or platform == 'flash':
                manifest_url = update_url_query(
                    media_url.replace('manifest#live_hds.f4m', 'manifest.f4m'),
                    {'hdcore': '3.7.0', 'plugin': 'aasp-3.7.0.39.44'})
                formats.extend(self._extract_f4m_formats(
                    manifest_url, video_id, f4m_id='hds', fatal=False))
            else:
                bitrate = int_or_none(xpath_text(relinker, 'bitrate'))
                formats.append({
                    'url': media_url,
                    'tbr': bitrate if bitrate > 0 else None,
                    'format_id': 'http-%d' % bitrate if bitrate > 0 else 'http',
                })

        if not formats and geoprotection is True:
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)

        if not audio_only:
            formats.extend(self._create_http_urls(relinker_url, formats))

        return filter_dict({
            'is_live': is_live,
            'duration': duration,
            'formats': formats,
        })

    def _create_http_urls(self, relinker_url, fmts):
        _RELINKER_REG = r'https?://(?P<host>[^/]+?)/(?:i/)?(?P<extra>[^/]+?)/(?P<path>.+?)/(?P<id>\w+)(?:_(?P<quality>[\d\,]+))?(?:\.mp4|/playlist\.m3u8).+?'
        _MP4_TMPL = '%s&overrideUserAgentRule=mp4-%s'
        _QUALITY = {
            # tbr: w, h
            '250': [352, 198],
            '400': [512, 288],
            '700': [512, 288],
            '800': [700, 394],
            '1200': [736, 414],
            '1800': [1024, 576],
            '2400': [1280, 720],
            '3200': [1440, 810],
            '3600': [1440, 810],
            '5000': [1920, 1080],
            '10000': [1920, 1080],
        }

        def test_url(url):
            resp = self._request_webpage(
                HEADRequest(url), None, headers={'User-Agent': 'Rai'},
                fatal=False, errnote=False, note=False)

            if resp is False:
                return False

            if resp.code == 200:
                return False if resp.url == url else resp.url
            return None

        # filter out audio-only formats
        fmts = [f for f in fmts if not f.get('vcodec') == 'none']

        def get_format_info(tbr):
            import math
            br = int_or_none(tbr)
            if len(fmts) == 1 and not br:
                br = fmts[0].get('tbr')
            if br > 300:
                tbr = compat_str(math.floor(br / 100) * 100)
            else:
                tbr = '250'

            # try extracting info from available m3u8 formats
            format_copy = None
            for f in fmts:
                if f.get('tbr'):
                    br_limit = math.floor(br / 100)
                    if br_limit - 1 <= math.floor(f['tbr'] / 100) <= br_limit + 1:
                        format_copy = f.copy()
            return {
                'width': format_copy.get('width'),
                'height': format_copy.get('height'),
                'tbr': format_copy.get('tbr'),
                'vcodec': format_copy.get('vcodec'),
                'acodec': format_copy.get('acodec'),
                'fps': format_copy.get('fps'),
                'format_id': 'https-%s' % tbr,
            } if format_copy else {
                'width': _QUALITY[tbr][0],
                'height': _QUALITY[tbr][1],
                'format_id': 'https-%s' % tbr,
                'tbr': int(tbr),
            }

        loc = test_url(_MP4_TMPL % (relinker_url, '*'))
        if not isinstance(loc, compat_str):
            return []

        mobj = re.match(
            _RELINKER_REG,
            test_url(relinker_url) or '')
        if not mobj:
            return []

        available_qualities = mobj.group('quality').split(',') if mobj.group('quality') else ['*']
        available_qualities = [i for i in available_qualities if i]

        formats = []
        for q in available_qualities:
            fmt = {
                'url': _MP4_TMPL % (relinker_url, q),
                'protocol': 'https',
                'ext': 'mp4',
            }
            fmt.update(get_format_info(q))
            formats.append(fmt)
        return formats

    @staticmethod
    def _extract_subtitles(url, video_data):
        STL_EXT = 'stl'
        SRT_EXT = 'srt'
        subtitles = {}
        subtitles_array = video_data.get('subtitlesArray') or []
        for k in ('subtitles', 'subtitlesUrl'):
            subtitles_array.append({'url': video_data.get(k)})
        for subtitle in subtitles_array:
            sub_url = subtitle.get('url')
            if sub_url and isinstance(sub_url, compat_str):
                sub_lang = subtitle.get('language') or 'it'
                sub_url = urljoin(url, sub_url)
                sub_ext = determine_ext(sub_url, SRT_EXT)
                subtitles.setdefault(sub_lang, []).append({
                    'ext': sub_ext,
                    'url': sub_url,
                })
                if STL_EXT == sub_ext:
                    subtitles[sub_lang].append({
                        'ext': SRT_EXT,
                        'url': sub_url[:-len(STL_EXT)] + SRT_EXT,
                    })
        return subtitles


class RaiPlayIE(RaiBaseIE):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplay\.it/.+?-(?P<id>%s))\.(?:html|json)' % RaiBaseIE._UUID_RE
    _TESTS = [{
        'url': 'http://www.raiplay.it/video/2014/04/Report-del-07042014-cb27157f-9dd0-4aee-b788-b1f67643a391.html',
        'md5': '8970abf8caf8aef4696e7b1f2adfc696',
        'info_dict': {
            'id': 'cb27157f-9dd0-4aee-b788-b1f67643a391',
            'ext': 'mp4',
            'title': 'Report del 07/04/2014',
            'alt_title': 'St 2013/14 - Report - Espresso nel caffè - 07/04/2014',
            'description': 'md5:d730c168a58f4bb35600fc2f881ec04e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Rai Gulp',
            'duration': 6160,
            'series': 'Report',
            'season': '2013/14',
            'subtitles': {
                'it': 'count:4',
            },
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # 1080p direct mp4 url
        'url': 'https://www.raiplay.it/video/2021/11/Blanca-S1E1-Senza-occhi-b1255a4a-8e72-4a2f-b9f3-fc1308e00736.html',
        'md5': 'aeda7243115380b2dd5e881fd42d949a',
        'info_dict': {
            'id': 'b1255a4a-8e72-4a2f-b9f3-fc1308e00736',
            'ext': 'mp4',
            'title': 'Blanca - S1E1 - Senza occhi',
            'alt_title': 'St 1 Ep 1 - Blanca - Senza occhi',
            'description': 'md5:75f95d5c030ec8bac263b1212322e28c',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Rai 1',
            'duration': 6493,
            'series': 'Blanca',
            'season': 'Season 1',
        },
    }, {
        'url': 'http://www.raiplay.it/video/2016/11/gazebotraindesi-efebe701-969c-4593-92f3-285f0d1ce750.html?',
        'only_matching': True,
    }, {
        # subtitles at 'subtitlesArray' key (see #27698)
        'url': 'https://www.raiplay.it/video/2020/12/Report---04-01-2021-2e90f1de-8eee-4de4-ac0e-78d21db5b600.html',
        'only_matching': True,
    }, {
        # DRM protected
        'url': 'https://www.raiplay.it/video/2020/09/Lo-straordinario-mondo-di-Zoey-S1E1-Lo-straordinario-potere-di-Zoey-ed493918-1d32-44b7-8454-862e473d00ff.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        base, video_id = self._match_valid_url(url).groups()

        media = self._download_json(
            base + '.json', video_id, 'Downloading video JSON')

        if not self.get_param('allow_unplayable_formats'):
            if try_get(
                    media,
                    (lambda x: x['rights_management']['rights']['drm'],
                     lambda x: x['program_info']['rights_management']['rights']['drm']),
                    dict):
                self.report_drm(video_id)

        title = media['name']
        video = media['video']

        relinker_info = self._extract_relinker_info(video['content_url'], video_id)
        self._sort_formats(relinker_info['formats'])

        thumbnails = []
        for _, value in media.get('images', {}).items():
            if value:
                thumbnails.append({
                    'url': urljoin(url, value),
                })

        date_published = media.get('date_published')
        time_published = media.get('time_published')
        if date_published and time_published:
            date_published += ' ' + time_published

        subtitles = self._extract_subtitles(url, video)

        program_info = media.get('program_info') or {}
        season = media.get('season')

        alt_title = join_nonempty(media.get('subtitle'), media.get('toptitle'), delim=' - ')

        info = {
            'id': remove_start(media.get('id'), 'ContentItem-') or video_id,
            'display_id': video_id,
            'title': title,
            'alt_title': strip_or_none(alt_title),
            'description': media.get('description'),
            'uploader': strip_or_none(media.get('channel')),
            'creator': strip_or_none(media.get('editor') or None),
            'duration': parse_duration(video.get('duration')),
            'timestamp': unified_timestamp(date_published),
            'thumbnails': thumbnails,
            'series': program_info.get('name'),
            'season_number': int_or_none(season),
            'season': season if (season and not season.isdigit()) else None,
            'episode': media.get('episode_title'),
            'episode_number': int_or_none(media.get('episode')),
            'subtitles': subtitles,
            'release_year': traverse_obj(media, ('track_info', 'edit_year')),
        }

        info.update(relinker_info)
        return info


class RaiPlayLiveIE(RaiPlayIE):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplay\.it/dirette/(?P<id>[^/?#&]+))'
    _TESTS = [{
        'url': 'http://www.raiplay.it/dirette/rainews24',
        'info_dict': {
            'id': 'd784ad40-e0ae-4a69-aa76-37519d238a9c',
            'display_id': 'rainews24',
            'ext': 'mp4',
            'title': 're:^Diretta di Rai News 24 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'md5:4d00bcf6dc98b27c6ec480de329d1497',
            'uploader': 'Rai News 24',
            'creator': 'Rai News 24',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }]


class RaiPlayPlaylistIE(InfoExtractor):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplay\.it/programmi/(?P<id>[^/?#&]+))(?:/(?P<extra_id>[^?#&]+))?'
    _TESTS = [{
        'url': 'https://www.raiplay.it/programmi/nondirloalmiocapo/',
        'info_dict': {
            'id': 'nondirloalmiocapo',
            'title': 'Non dirlo al mio capo',
            'description': 'md5:98ab6b98f7f44c2843fd7d6f045f153b',
        },
        'playlist_mincount': 12,
    }, {
        'url': 'https://www.raiplay.it/programmi/nondirloalmiocapo/episodi/stagione-2/',
        'info_dict': {
            'id': 'nondirloalmiocapo',
            'title': 'Non dirlo al mio capo - Stagione 2',
            'description': 'md5:98ab6b98f7f44c2843fd7d6f045f153b',
        },
        'playlist_mincount': 12,
    }]

    def _real_extract(self, url):
        base, playlist_id, extra_id = self._match_valid_url(url).groups()

        program = self._download_json(
            base + '.json', playlist_id, 'Downloading program JSON')

        if extra_id:
            extra_id = extra_id.upper().rstrip('/')

        playlist_title = program.get('name')
        entries = []
        for b in (program.get('blocks') or []):
            for s in (b.get('sets') or []):
                if extra_id:
                    if extra_id != join_nonempty(
                            b.get('name'), s.get('name'), delim='/').replace(' ', '-').upper():
                        continue
                    playlist_title = join_nonempty(playlist_title, s.get('name'), delim=' - ')

                s_id = s.get('id')
                if not s_id:
                    continue
                medias = self._download_json(
                    '%s/%s.json' % (base, s_id), s_id,
                    'Downloading content set JSON', fatal=False)
                if not medias:
                    continue
                for m in (medias.get('items') or []):
                    path_id = m.get('path_id')
                    if not path_id:
                        continue
                    video_url = urljoin(url, path_id)
                    entries.append(self.url_result(
                        video_url, ie=RaiPlayIE.ie_key(),
                        video_id=RaiPlayIE._match_id(video_url)))

        return self.playlist_result(
            entries, playlist_id, playlist_title,
            try_get(program, lambda x: x['program_info']['description']))


class RaiPlaySoundIE(RaiBaseIE):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplaysound\.it/.+?-(?P<id>%s))\.(?:html|json)' % RaiBaseIE._UUID_RE
    _TESTS = [{
        'url': 'https://www.raiplaysound.it/audio/2021/12/IL-RUGGITO-DEL-CONIGLIO-1ebae2a7-7cdb-42bb-842e-fe0d193e9707.html',
        'md5': '8970abf8caf8aef4696e7b1f2adfc696',
        'info_dict': {
            'id': '1ebae2a7-7cdb-42bb-842e-fe0d193e9707',
            'ext': 'mp3',
            'title': 'Il Ruggito del Coniglio del 10/12/2021',
            'description': 'md5:2a17d2107e59a4a8faa0e18334139ee2',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'rai radio 2',
            'duration': 5685,
            'series': 'Il Ruggito del Coniglio',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        base, audio_id = self._match_valid_url(url).group('base', 'id')
        media = self._download_json(f'{base}.json', audio_id, 'Downloading audio JSON')
        uid = try_get(media, lambda x: remove_start(remove_start(x['uniquename'], 'ContentItem-'), 'Page-'))

        info = {}
        formats = []
        relinkers = set(traverse_obj(media, (('downloadable_audio', 'audio', ('live', 'cards', 0, 'audio')), 'url')))
        for r in relinkers:
            info = self._extract_relinker_info(r, audio_id, True)
            formats.extend(info.get('formats'))

        date_published = try_get(media, (lambda x: f'{x["create_date"]} {x.get("create_time") or ""}',
                                         lambda x: x['live']['create_date']))

        podcast_info = traverse_obj(media, 'podcast_info', ('live', 'cards', 0)) or {}
        thumbnails = [{
            'url': urljoin(url, thumb_url),
        } for thumb_url in (podcast_info.get('images') or {}).values() if thumb_url]

        return {
            **info,
            'id': uid or audio_id,
            'display_id': audio_id,
            'title': traverse_obj(media, 'title', 'episode_title'),
            'alt_title': traverse_obj(media, ('track_info', 'media_name')),
            'description': media.get('description'),
            'uploader': traverse_obj(media, ('track_info', 'channel'), expected_type=strip_or_none),
            'creator': traverse_obj(media, ('track_info', 'editor'), expected_type=strip_or_none),
            'timestamp': unified_timestamp(date_published),
            'thumbnails': thumbnails,
            'series': podcast_info.get('title'),
            'season_number': int_or_none(media.get('season')),
            'episode': media.get('episode_title'),
            'episode_number': int_or_none(media.get('episode')),
            'formats': formats,
        }


class RaiPlaySoundLiveIE(RaiPlaySoundIE):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplaysound\.it/(?P<id>[^/?#&]+)$)'
    _TESTS = [{
        'url': 'https://www.raiplaysound.it/radio2',
        'info_dict': {
            'id': 'b00a50e6-f404-4af6-8f8c-ff3b9af73a44',
            'display_id': 'radio2',
            'ext': 'mp4',
            'title': 'Rai Radio 2',
            'uploader': 'rai radio 2',
            'creator': 'raiplaysound',
            'is_live': True,
        },
        'params': {
            'skip_download': 'live',
        },
    }]


class RaiPlaySoundPlaylistIE(InfoExtractor):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplaysound\.it/(?:programmi|playlist|audiolibri)/(?P<id>[^/?#&]+))(?:/(?P<extra_id>[^?#&]+))?'
    _TESTS = [{
        'url': 'https://www.raiplaysound.it/programmi/ilruggitodelconiglio',
        'info_dict': {
            'id': 'ilruggitodelconiglio',
            'title': 'Il Ruggito del Coniglio',
            'description': 'md5:1bbaf631245a7ab1ec4d9fbb3c7aa8f3',
        },
        'playlist_mincount': 65,
    }, {
        'url': 'https://www.raiplaysound.it/programmi/ilruggitodelconiglio/puntate/prima-stagione-1995',
        'info_dict': {
            'id': 'ilruggitodelconiglio_puntate_prima-stagione-1995',
            'title': 'Prima Stagione 1995',
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        base, playlist_id, extra_id = self._match_valid_url(url).group('base', 'id', 'extra_id')
        url = f'{base}.json'
        program = self._download_json(url, playlist_id, 'Downloading program JSON')

        if extra_id:
            extra_id = extra_id.rstrip('/')
            playlist_id += '_' + extra_id.replace('/', '_')
            path = next(c['path_id'] for c in program.get('filters') or [] if extra_id in c.get('weblink'))
            program = self._download_json(
                urljoin('https://www.raiplaysound.it', path), playlist_id, 'Downloading program secondary JSON')

        entries = [
            self.url_result(urljoin(base, c['path_id']), ie=RaiPlaySoundIE.ie_key())
            for c in traverse_obj(program, 'cards', ('block', 'cards')) or []
            if c.get('path_id')]

        return self.playlist_result(entries, playlist_id, program.get('title'),
                                    traverse_obj(program, ('podcast_info', 'description')))


class RaiIE(RaiBaseIE):
    _VALID_URL = r'https?://[^/]+\.(?:rai\.(?:it|tv)|rainews\.it)/.+?-(?P<id>%s)(?:-.+?)?\.html' % RaiBaseIE._UUID_RE
    _TESTS = [{
        # var uniquename = "ContentItem-..."
        # data-id="ContentItem-..."
        'url': 'http://www.raisport.rai.it/dl/raiSport/media/rassegna-stampa-04a9f4bd-b563-40cf-82a6-aad3529cb4a9.html',
        'info_dict': {
            'id': '04a9f4bd-b563-40cf-82a6-aad3529cb4a9',
            'ext': 'mp4',
            'title': 'TG PRIMO TEMPO',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1758,
            'upload_date': '20140612',
        },
        'skip': 'This content is available only in Italy',
    }, {
        # with ContentItem in many metas
        'url': 'http://www.rainews.it/dl/rainews/media/Weekend-al-cinema-da-Hollywood-arriva-il-thriller-di-Tate-Taylor-La-ragazza-del-treno-1632c009-c843-4836-bb65-80c33084a64b.html',
        'info_dict': {
            'id': '1632c009-c843-4836-bb65-80c33084a64b',
            'ext': 'mp4',
            'title': 'Weekend al cinema, da Hollywood arriva il thriller di Tate Taylor "La ragazza del treno"',
            'description': 'I film in uscita questa settimana.',
            'thumbnail': r're:^https?://.*\.png$',
            'duration': 833,
            'upload_date': '20161103',
        }
    }, {
        # with ContentItem in og:url
        'url': 'http://www.rai.it/dl/RaiTV/programmi/media/ContentItem-efb17665-691c-45d5-a60c-5301333cbb0c.html',
        'md5': '06345bd97c932f19ffb129973d07a020',
        'info_dict': {
            'id': 'efb17665-691c-45d5-a60c-5301333cbb0c',
            'ext': 'mp4',
            'title': 'TG1 ore 20:00 del 03/11/2016',
            'description': 'TG1 edizione integrale ore 20:00 del giorno 03/11/2016',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2214,
            'upload_date': '20161103',
        }
    }, {
        # initEdizione('ContentItem-...'
        'url': 'http://www.tg1.rai.it/dl/tg1/2010/edizioni/ContentSet-9b6e0cba-4bef-4aef-8cf0-9f7f665b7dfb-tg1.html?item=undefined',
        'info_dict': {
            'id': 'c2187016-8484-4e3a-8ac8-35e475b07303',
            'ext': 'mp4',
            'title': r're:TG1 ore \d{2}:\d{2} del \d{2}/\d{2}/\d{4}',
            'duration': 2274,
            'upload_date': '20170401',
        },
        'skip': 'Changes daily',
    }, {
        # HLS live stream with ContentItem in og:url
        'url': 'http://www.rainews.it/dl/rainews/live/ContentItem-3156f2f2-dc70-4953-8e2f-70d7489d4ce9.html',
        'info_dict': {
            'id': '3156f2f2-dc70-4953-8e2f-70d7489d4ce9',
            'ext': 'mp4',
            'title': 'La diretta di Rainews24',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Direct MMS URL
        'url': 'http://www.rai.it/dl/RaiTV/programmi/media/ContentItem-b63a4089-ac28-48cf-bca5-9f5b5bc46df5.html',
        'only_matching': True,
    }, {
        'url': 'https://www.rainews.it/tgr/marche/notiziari/video/2019/02/ContentItem-6ba945a2-889c-4a80-bdeb-8489c70a8db9.html',
        'only_matching': True,
    }]

    def _extract_from_content_id(self, content_id, url):
        media = self._download_json(
            'http://www.rai.tv/dl/RaiTV/programmi/media/ContentItem-%s.html?json' % content_id,
            content_id, 'Downloading video JSON')

        title = media['name'].strip()

        media_type = media['type']
        if 'Audio' in media_type:
            relinker_info = {
                'formats': [{
                    'format_id': media.get('formatoAudio'),
                    'url': media['audioUrl'],
                    'ext': media.get('formatoAudio'),
                }]
            }
        elif 'Video' in media_type:
            relinker_info = self._extract_relinker_info(media['mediaUri'], content_id)
        else:
            raise ExtractorError('not a media file')

        self._sort_formats(relinker_info['formats'])

        thumbnails = []
        for image_type in ('image', 'image_medium', 'image_300'):
            thumbnail_url = media.get(image_type)
            if thumbnail_url:
                thumbnails.append({
                    'url': compat_urlparse.urljoin(url, thumbnail_url),
                })

        subtitles = self._extract_subtitles(url, media)

        info = {
            'id': content_id,
            'title': title,
            'description': strip_or_none(media.get('desc')),
            'thumbnails': thumbnails,
            'uploader': media.get('author'),
            'upload_date': unified_strdate(media.get('date')),
            'duration': parse_duration(media.get('length')),
            'subtitles': subtitles,
        }

        info.update(relinker_info)

        return info

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        content_item_id = None

        content_item_url = self._html_search_meta(
            ('og:url', 'og:video', 'og:video:secure_url', 'twitter:url',
             'twitter:player', 'jsonlink'), webpage, default=None)
        if content_item_url:
            content_item_id = self._search_regex(
                r'ContentItem-(%s)' % self._UUID_RE, content_item_url,
                'content item id', default=None)

        if not content_item_id:
            content_item_id = self._search_regex(
                r'''(?x)
                    (?:
                        (?:initEdizione|drawMediaRaiTV)\(|
                        <(?:[^>]+\bdata-id|var\s+uniquename)=|
                        <iframe[^>]+\bsrc=
                    )
                    (["\'])
                    (?:(?!\1).)*\bContentItem-(?P<id>%s)
                ''' % self._UUID_RE,
                webpage, 'content item id', default=None, group='id')

        content_item_ids = set()
        if content_item_id:
            content_item_ids.add(content_item_id)
        if video_id not in content_item_ids:
            content_item_ids.add(video_id)

        for content_item_id in content_item_ids:
            try:
                return self._extract_from_content_id(content_item_id, url)
            except GeoRestrictedError:
                raise
            except ExtractorError:
                pass

        relinker_url = self._proto_relative_url(self._search_regex(
            r'''(?x)
                (?:
                    var\s+videoURL|
                    mediaInfo\.mediaUri
                )\s*=\s*
                ([\'"])
                (?P<url>
                    (?:https?:)?
                    //mediapolis(?:vod)?\.rai\.it/relinker/relinkerServlet\.htm\?
                    (?:(?!\1).)*\bcont=(?:(?!\1).)+)\1
            ''',
            webpage, 'relinker URL', group='url'))

        relinker_info = self._extract_relinker_info(
            urljoin(url, relinker_url), video_id)
        self._sort_formats(relinker_info['formats'])

        title = self._search_regex(
            r'var\s+videoTitolo\s*=\s*([\'"])(?P<title>[^\'"]+)\1',
            webpage, 'title', group='title',
            default=None) or self._og_search_title(webpage)

        info = {
            'id': video_id,
            'title': title,
        }

        info.update(relinker_info)

        return info
