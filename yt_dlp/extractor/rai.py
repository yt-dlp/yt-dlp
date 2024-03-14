import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    filter_dict,
    GeoRestrictedError,
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

    def _fix_m3u8_formats(self, media_url, video_id):
        fmts = self._extract_m3u8_formats(
            media_url, video_id, 'mp4', m3u8_id='hls', fatal=False)

        # Fix malformed m3u8 manifests by setting audio-only/video-only formats
        for f in fmts:
            if not f.get('acodec'):
                f['acodec'] = 'mp4a'
            if not f.get('vcodec'):
                f['vcodec'] = 'avc1'
            man_url = f['url']
            if re.search(r'chunklist(?:_b\d+)*_ao[_.]', man_url):  # audio only
                f['vcodec'] = 'none'
            elif re.search(r'chunklist(?:_b\d+)*_vo[_.]', man_url):  # video only
                f['acodec'] = 'none'
            else:  # video+audio
                if f['acodec'] == 'none':
                    f['acodec'] = 'mp4a'
                if f['vcodec'] == 'none':
                    f['vcodec'] = 'avc1'

        return fmts

    def _extract_relinker_info(self, relinker_url, video_id, audio_only=False):
        def fix_cdata(s):
            # remove \r\n\t before and after <![CDATA[ ]]> to avoid
            # polluted text with xpath_text
            s = re.sub(r'(\]\]>)[\r\n\t]+(</)', '\\1\\2', s)
            return re.sub(r'(>)[\r\n\t]+(<!\[CDATA\[)', '\\1\\2', s)

        if not re.match(r'https?://', relinker_url):
            return {'formats': [{'url': relinker_url}]}

        # set User-Agent to generic 'Rai' to avoid quality filtering from
        # the media server and get the maximum qualities available
        relinker = self._download_xml(
            relinker_url, video_id, note='Downloading XML metadata',
            transform_source=fix_cdata, query={'output': 64},
            headers={**self.geo_verification_headers(), 'User-Agent': 'Rai'})

        if xpath_text(relinker, './license_url', default='{}') != '{}':
            self.report_drm(video_id)

        is_live = xpath_text(relinker, './is_live', default='N') == 'Y'
        duration = parse_duration(xpath_text(relinker, './duration', default=None))
        media_url = xpath_text(relinker, './url[@type="content"]', default=None)

        if not media_url:
            self.raise_no_formats('The relinker returned no media url')

        # geo flag is a bit unreliable and not properly set all the time
        geoprotection = xpath_text(relinker, './geoprotection', default='N') == 'Y'

        ext = determine_ext(media_url)
        formats = []

        if ext == 'mp3':
            formats.append({
                'url': media_url,
                'vcodec': 'none',
                'acodec': 'mp3',
                'format_id': 'https-mp3',
            })
        elif ext == 'm3u8' or 'format=m3u8' in media_url:
            formats.extend(self._fix_m3u8_formats(media_url, video_id))
        elif ext == 'f4m':
            # very likely no longer needed. Cannot find any url that uses it.
            manifest_url = update_url_query(
                media_url.replace('manifest#live_hds.f4m', 'manifest.f4m'),
                {'hdcore': '3.7.0', 'plugin': 'aasp-3.7.0.39.44'})
            formats.extend(self._extract_f4m_formats(
                manifest_url, video_id, f4m_id='hds', fatal=False))
        elif ext == 'mp4':
            bitrate = int_or_none(xpath_text(relinker, './bitrate'))
            formats.append({
                'url': media_url,
                'tbr': bitrate if bitrate > 0 else None,
                'format_id': join_nonempty('https', bitrate, delim='-'),
            })
        else:
            raise ExtractorError('Unrecognized media file found')

        if (not formats and geoprotection is True) or '/video_no_available.mp4' in media_url:
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)

        if not audio_only and not is_live:
            formats.extend(self._create_http_urls(media_url, relinker_url, formats, video_id))

        return filter_dict({
            'is_live': is_live,
            'duration': duration,
            'formats': formats,
        })

    def _create_http_urls(self, manifest_url, relinker_url, fmts, video_id):
        _MANIFEST_REG = r'/(?P<id>\w+)(?:_(?P<quality>[\d\,]+))?(?:\.mp4)?(?:\.csmil)?/playlist\.m3u8'
        _MP4_TMPL = '%s&overrideUserAgentRule=mp4-%s'
        _QUALITY = {
            # tbr: w, h
            250: [352, 198],
            400: [512, 288],
            600: [512, 288],
            700: [512, 288],
            800: [700, 394],
            1200: [736, 414],
            1500: [920, 518],
            1800: [1024, 576],
            2400: [1280, 720],
            3200: [1440, 810],
            3600: [1440, 810],
            5000: [1920, 1080],
            10000: [1920, 1080],
        }

        def percentage(number, target, pc=20, roof=125):
            '''check if the target is in the range of number +/- percent'''
            if not number or number < 0:
                return False
            return abs(target - number) < min(float(number) * float(pc) / 100.0, roof)

        def get_format_info(tbr):
            import math
            br = int_or_none(tbr)
            if len(fmts) == 1 and not br:
                br = fmts[0].get('tbr')
            if br and br > 300:
                tbr = math.floor(br / 100) * 100
            else:
                tbr = 250

            # try extracting info from available m3u8 formats
            format_copy = [None, None]
            for f in fmts:
                if f.get('tbr'):
                    if percentage(tbr, f['tbr']):
                        format_copy[0] = f.copy()
                if [f.get('width'), f.get('height')] == _QUALITY.get(tbr):
                    format_copy[1] = f.copy()
                    format_copy[1]['tbr'] = tbr

            # prefer format with similar bitrate because there might be
            # multiple video with the same resolution but different bitrate
            format_copy = format_copy[0] or format_copy[1] or {}
            return {
                'format_id': f'https-{tbr}',
                'width': format_copy.get('width'),
                'height': format_copy.get('height'),
                'tbr': format_copy.get('tbr') or tbr,
                'vcodec': format_copy.get('vcodec') or 'avc1',
                'acodec': format_copy.get('acodec') or 'mp4a',
                'fps': format_copy.get('fps') or 25,
            } if format_copy else {
                'format_id': f'https-{tbr}',
                'width': _QUALITY[tbr][0],
                'height': _QUALITY[tbr][1],
                'tbr': tbr,
                'vcodec': 'avc1',
                'acodec': 'mp4a',
                'fps': 25,
            }

        # Check if MP4 download is available
        try:
            self._request_webpage(
                HEADRequest(_MP4_TMPL % (relinker_url, '*')), video_id, 'Checking MP4 availability')
        except ExtractorError as e:
            self.to_screen(f'{video_id}: MP4 direct download is not available: {e.cause}')
            return []

        # filter out single-stream formats
        fmts = [f for f in fmts
                if not f.get('vcodec') == 'none' and not f.get('acodec') == 'none']

        mobj = re.search(_MANIFEST_REG, manifest_url)
        if not mobj:
            return []
        available_qualities = mobj.group('quality').split(',') if mobj.group('quality') else ['*']

        formats = []
        for q in filter(None, available_qualities):
            self.write_debug(f'Creating https format for quality {q}')
            formats.append({
                'url': _MP4_TMPL % (relinker_url, q),
                'protocol': 'https',
                'ext': 'mp4',
                **get_format_info(q)
            })
        return formats

    @staticmethod
    def _get_thumbnails_list(thumbs, url):
        return [{
            'url': urljoin(url, thumb_url),
        } for thumb_url in (thumbs or {}).values() if thumb_url]

    @staticmethod
    def _extract_subtitles(url, video_data):
        STL_EXT = 'stl'
        SRT_EXT = 'srt'
        subtitles = {}
        subtitles_array = video_data.get('subtitlesArray') or video_data.get('subtitleList') or []
        for k in ('subtitles', 'subtitlesUrl'):
            subtitles_array.append({'url': video_data.get(k)})
        for subtitle in subtitles_array:
            sub_url = subtitle.get('url')
            if sub_url and isinstance(sub_url, str):
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
    _VALID_URL = rf'(?P<base>https?://(?:www\.)?raiplay\.it/.+?-(?P<id>{RaiBaseIE._UUID_RE}))\.(?:html|json)'
    _TESTS = [{
        'url': 'https://www.raiplay.it/video/2014/04/Report-del-07042014-cb27157f-9dd0-4aee-b788-b1f67643a391.html',
        'md5': '8970abf8caf8aef4696e7b1f2adfc696',
        'info_dict': {
            'id': 'cb27157f-9dd0-4aee-b788-b1f67643a391',
            'ext': 'mp4',
            'title': 'Report del 07/04/2014',
            'alt_title': 'St 2013/14 - Report - Espresso nel caffè - 07/04/2014',
            'description': 'md5:d730c168a58f4bb35600fc2f881ec04e',
            'thumbnail': r're:^https?://www\.raiplay\.it/.+\.jpg',
            'uploader': 'Rai 3',
            'creator': 'Rai 3',
            'duration': 6160,
            'series': 'Report',
            'season': '2013/14',
            'subtitles': {'it': 'count:4'},
            'release_year': 2024,
            'episode': 'Espresso nel caffè - 07/04/2014',
            'timestamp': 1396919880,
            'upload_date': '20140408',
            'formats': 'count:4',
        },
        'params': {'skip_download': True},
    }, {
        # 1080p
        'url': 'https://www.raiplay.it/video/2021/11/Blanca-S1E1-Senza-occhi-b1255a4a-8e72-4a2f-b9f3-fc1308e00736.html',
        'md5': 'aeda7243115380b2dd5e881fd42d949a',
        'info_dict': {
            'id': 'b1255a4a-8e72-4a2f-b9f3-fc1308e00736',
            'ext': 'mp4',
            'title': 'Blanca - S1E1 - Senza occhi',
            'alt_title': 'St 1 Ep 1 - Blanca - Senza occhi',
            'description': 'md5:75f95d5c030ec8bac263b1212322e28c',
            'thumbnail': r're:^https://www\.raiplay\.it/dl/img/.+\.jpg',
            'uploader': 'Rai Premium',
            'creator': 'Rai Fiction',
            'duration': 6493,
            'series': 'Blanca',
            'season': 'Season 1',
            'episode_number': 1,
            'release_year': 2021,
            'season_number': 1,
            'episode': 'Senza occhi',
            'timestamp': 1637318940,
            'upload_date': '20211119',
            'formats': 'count:7',
        },
        'params': {'skip_download': True},
        'expected_warnings': ['Video not available. Likely due to geo-restriction.']
    }, {
        # 1500 quality
        'url': 'https://www.raiplay.it/video/2012/09/S1E11---Tutto-cio-che-luccica-0cab3323-732e-45d6-8e86-7704acab6598.html',
        'md5': 'a634d20e8ab2d43724c273563f6bf87a',
        'info_dict': {
            'id': '0cab3323-732e-45d6-8e86-7704acab6598',
            'ext': 'mp4',
            'title': 'Mia and Me - S1E11 - Tutto ciò che luccica',
            'alt_title': 'St 1 Ep 11 - Mia and Me - Tutto ciò che luccica',
            'description': 'md5:4969e594184b1920c4c1f2b704da9dea',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Rai Gulp',
            'series': 'Mia and Me',
            'season': 'Season 1',
            'episode_number': 11,
            'release_year': 2015,
            'season_number': 1,
            'episode': 'Tutto ciò che luccica',
            'timestamp': 1348495020,
            'upload_date': '20120924',
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
        'url': 'https://www.raiplay.it/video/2021/06/Lo-straordinario-mondo-di-Zoey-S2E1-Lo-straordinario-ritorno-di-Zoey-3ba992de-2332-41ad-9214-73e32ab209f4.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        base, video_id = self._match_valid_url(url).groups()

        media = self._download_json(
            f'{base}.json', video_id, 'Downloading video JSON')

        if not self.get_param('allow_unplayable_formats'):
            if traverse_obj(media, (('program_info', None), 'rights_management', 'rights', 'drm')):
                self.report_drm(video_id)

        video = media['video']
        relinker_info = self._extract_relinker_info(video['content_url'], video_id)
        date_published = join_nonempty(
            media.get('date_published'), media.get('time_published'), delim=' ')
        season = media.get('season')
        alt_title = join_nonempty(media.get('subtitle'), media.get('toptitle'), delim=' - ')

        return {
            'id': remove_start(media.get('id'), 'ContentItem-') or video_id,
            'display_id': video_id,
            'title': media.get('name'),
            'alt_title': strip_or_none(alt_title or None),
            'description': media.get('description'),
            'uploader': strip_or_none(
                traverse_obj(media, ('program_info', 'channel'))
                or media.get('channel') or None),
            'creator': strip_or_none(
                traverse_obj(media, ('program_info', 'editor'))
                or media.get('editor') or None),
            'duration': parse_duration(video.get('duration')),
            'timestamp': unified_timestamp(date_published),
            'thumbnails': self._get_thumbnails_list(media.get('images'), url),
            'series': traverse_obj(media, ('program_info', 'name')),
            'season_number': int_or_none(season),
            'season': season if (season and not season.isdigit()) else None,
            'episode': media.get('episode_title'),
            'episode_number': int_or_none(media.get('episode')),
            'subtitles': self._extract_subtitles(url, video),
            'release_year': int_or_none(traverse_obj(media, ('track_info', 'edit_year'))),
            **relinker_info
        }


class RaiPlayLiveIE(RaiPlayIE):  # XXX: Do not subclass from concrete IE
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
            'live_status': 'is_live',
            'upload_date': '20090502',
            'timestamp': 1241276220,
            'formats': 'count:3',
        },
        'params': {'skip_download': True},
    }]


class RaiPlayPlaylistIE(InfoExtractor):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplay\.it/programmi/(?P<id>[^/?#&]+))(?:/(?P<extra_id>[^?#&]+))?'
    _TESTS = [{
        # entire series episodes + extras...
        'url': 'https://www.raiplay.it/programmi/nondirloalmiocapo/',
        'info_dict': {
            'id': 'nondirloalmiocapo',
            'title': 'Non dirlo al mio capo',
            'description': 'md5:98ab6b98f7f44c2843fd7d6f045f153b',
        },
        'playlist_mincount': 30,
    }, {
        # single season
        'url': 'https://www.raiplay.it/programmi/nondirloalmiocapo/episodi/stagione-2/',
        'info_dict': {
            'id': 'nondirloalmiocapo',
            'title': 'Non dirlo al mio capo - Stagione 2',
            'description': 'md5:98ab6b98f7f44c2843fd7d6f045f153b',
        },
        'playlist_count': 12,
    }]

    def _real_extract(self, url):
        base, playlist_id, extra_id = self._match_valid_url(url).groups()

        program = self._download_json(
            f'{base}.json', playlist_id, 'Downloading program JSON')

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
                    f'{base}/{s_id}.json', s_id,
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
    _VALID_URL = rf'(?P<base>https?://(?:www\.)?raiplaysound\.it/.+?-(?P<id>{RaiBaseIE._UUID_RE}))\.(?:html|json)'
    _TESTS = [{
        'url': 'https://www.raiplaysound.it/audio/2021/12/IL-RUGGITO-DEL-CONIGLIO-1ebae2a7-7cdb-42bb-842e-fe0d193e9707.html',
        'md5': '8970abf8caf8aef4696e7b1f2adfc696',
        'info_dict': {
            'id': '1ebae2a7-7cdb-42bb-842e-fe0d193e9707',
            'ext': 'mp3',
            'title': 'Il Ruggito del Coniglio del 10/12/2021',
            'alt_title': 'md5:0e6476cd57858bb0f3fcc835d305b455',
            'description': 'md5:2a17d2107e59a4a8faa0e18334139ee2',
            'thumbnail': r're:^https?://.+\.jpg$',
            'uploader': 'rai radio 2',
            'duration': 5685,
            'series': 'Il Ruggito del Coniglio',
            'episode': 'Il Ruggito del Coniglio del 10/12/2021',
            'creator': 'rai radio 2',
            'timestamp': 1638346620,
            'upload_date': '20211201',
        },
        'params': {'skip_download': True},
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

        return {
            **info,
            'id': uid or audio_id,
            'display_id': audio_id,
            'title': traverse_obj(media, 'title', 'episode_title'),
            'alt_title': traverse_obj(media, ('track_info', 'media_name'), expected_type=strip_or_none),
            'description': media.get('description'),
            'uploader': traverse_obj(media, ('track_info', 'channel'), expected_type=strip_or_none),
            'creator': traverse_obj(media, ('track_info', 'editor'), expected_type=strip_or_none),
            'timestamp': unified_timestamp(date_published),
            'thumbnails': self._get_thumbnails_list(podcast_info.get('images'), url),
            'series': podcast_info.get('title'),
            'season_number': int_or_none(media.get('season')),
            'episode': media.get('episode_title'),
            'episode_number': int_or_none(media.get('episode')),
            'formats': formats,
        }


class RaiPlaySoundLiveIE(RaiPlaySoundIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplaysound\.it/(?P<id>[^/?#&]+)$)'
    _TESTS = [{
        'url': 'https://www.raiplaysound.it/radio2',
        'info_dict': {
            'id': 'b00a50e6-f404-4af6-8f8c-ff3b9af73a44',
            'display_id': 'radio2',
            'ext': 'mp4',
            'title': r're:Rai Radio 2 \d+-\d+-\d+ \d+:\d+',
            'thumbnail': r're:^https://www\.raiplaysound\.it/dl/img/.+\.png',
            'uploader': 'rai radio 2',
            'series': 'Rai Radio 2',
            'creator': 'raiplaysound',
            'is_live': True,
            'live_status': 'is_live',
        },
        'params': {'skip_download': True},
    }]


class RaiPlaySoundPlaylistIE(InfoExtractor):
    _VALID_URL = r'(?P<base>https?://(?:www\.)?raiplaysound\.it/(?:programmi|playlist|audiolibri)/(?P<id>[^/?#&]+))(?:/(?P<extra_id>[^?#&]+))?'
    _TESTS = [{
        # entire show
        'url': 'https://www.raiplaysound.it/programmi/ilruggitodelconiglio',
        'info_dict': {
            'id': 'ilruggitodelconiglio',
            'title': 'Il Ruggito del Coniglio',
            'description': 'md5:62a627b3a2d0635d08fa8b6e0a04f27e',
        },
        'playlist_mincount': 65,
    }, {
        # single season
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
    _VALID_URL = rf'https?://[^/]+\.(?:rai\.(?:it|tv))/.+?-(?P<id>{RaiBaseIE._UUID_RE})(?:-.+?)?\.html'
    _TESTS = [{
        'url': 'https://www.raisport.rai.it/dl/raiSport/media/rassegna-stampa-04a9f4bd-b563-40cf-82a6-aad3529cb4a9.html',
        'info_dict': {
            'id': '04a9f4bd-b563-40cf-82a6-aad3529cb4a9',
            'ext': 'mp4',
            'title': 'TG PRIMO TEMPO',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 1758,
            'upload_date': '20140612',
        },
        'params': {'skip_download': True},
        'expected_warnings': ['Video not available. Likely due to geo-restriction.']
    }, {
        'url': 'https://www.rai.it/dl/RaiTV/programmi/media/ContentItem-efb17665-691c-45d5-a60c-5301333cbb0c.html',
        'info_dict': {
            'id': 'efb17665-691c-45d5-a60c-5301333cbb0c',
            'ext': 'mp4',
            'title': 'TG1 ore 20:00 del 03/11/2016',
            'description': 'TG1 edizione integrale ore 20:00 del giorno 03/11/2016',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2214,
            'upload_date': '20161103'
        },
        'params': {'skip_download': True},
    }, {
        # Direct MMS: Media URL no longer works.
        'url': 'http://www.rai.it/dl/RaiTV/programmi/media/ContentItem-b63a4089-ac28-48cf-bca5-9f5b5bc46df5.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        content_id = self._match_id(url)
        media = self._download_json(
            f'https://www.rai.tv/dl/RaiTV/programmi/media/ContentItem-{content_id}.html?json',
            content_id, 'Downloading video JSON', fatal=False, expected_status=404)

        if media is None:
            return None

        if 'Audio' in media['type']:
            relinker_info = {
                'formats': [{
                    'format_id': join_nonempty('https', media.get('formatoAudio'), delim='-'),
                    'url': media['audioUrl'],
                    'ext': media.get('formatoAudio'),
                    'vcodec': 'none',
                    'acodec': media.get('formatoAudio'),
                }]
            }
        elif 'Video' in media['type']:
            relinker_info = self._extract_relinker_info(media['mediaUri'], content_id)
        else:
            raise ExtractorError('not a media file')

        thumbnails = self._get_thumbnails_list(
            {image_type: media.get(image_type) for image_type in (
                'image', 'image_medium', 'image_300')}, url)

        return {
            'id': content_id,
            'title': strip_or_none(media.get('name') or media.get('title')),
            'description': strip_or_none(media.get('desc')) or None,
            'thumbnails': thumbnails,
            'uploader': strip_or_none(media.get('author')) or None,
            'upload_date': unified_strdate(media.get('date')),
            'duration': parse_duration(media.get('length')),
            'subtitles': self._extract_subtitles(url, media),
            **relinker_info
        }


class RaiNewsIE(RaiBaseIE):
    _VALID_URL = rf'https?://(www\.)?rainews\.it/(?!articoli)[^?#]+-(?P<id>{RaiBaseIE._UUID_RE})(?:-[^/?#]+)?\.html'
    _EMBED_REGEX = [rf'<iframe[^>]+data-src="(?P<url>/iframe/[^?#]+?{RaiBaseIE._UUID_RE}\.html)']
    _TESTS = [{
        # new rainews player (#3911)
        'url': 'https://www.rainews.it/video/2024/02/membri-della-croce-rossa-evacuano-gli-abitanti-di-un-villaggio-nella-regione-ucraina-di-kharkiv-il-filmato-dallucraina--31e8017c-845c-43f5-9c48-245b43c3a079.html',
        'info_dict': {
            'id': '31e8017c-845c-43f5-9c48-245b43c3a079',
            'ext': 'mp4',
            'title': 'md5:1e81364b09de4a149042bac3c7d36f0b',
            'duration': 196,
            'upload_date': '20240225',
            'uploader': 'rainews',
            'formats': 'count:2',
        },
        'params': {'skip_download': True},
    }, {
        # old content with fallback method to extract media urls
        'url': 'https://www.rainews.it/dl/rainews/media/Weekend-al-cinema-da-Hollywood-arriva-il-thriller-di-Tate-Taylor-La-ragazza-del-treno-1632c009-c843-4836-bb65-80c33084a64b.html',
        'info_dict': {
            'id': '1632c009-c843-4836-bb65-80c33084a64b',
            'ext': 'mp4',
            'title': 'Weekend al cinema, da Hollywood arriva il thriller di Tate Taylor "La ragazza del treno"',
            'description': 'I film in uscita questa settimana.',
            'thumbnail': r're:^https?://.*\.png$',
            'duration': 833,
            'upload_date': '20161103',
            'formats': 'count:8',
        },
        'params': {'skip_download': True},
        'expected_warnings': ['unable to extract player_data'],
    }, {
        # iframe + drm
        'url': 'https://www.rainews.it/iframe/video/2022/07/euro2022-europei-calcio-femminile-italia-belgio-gol-0-1-video-4de06a69-de75-4e32-a657-02f0885f8118.html',
        'only_matching': True,
    }]
    _PLAYER_TAG = 'news'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        player_data = self._search_json(
            rf'<rai{self._PLAYER_TAG}-player\s*data=\'', webpage, 'player_data', video_id,
            transform_source=clean_html, default={})
        track_info = player_data.get('track_info')
        relinker_url = traverse_obj(player_data, 'mediapolis', 'content_url')

        if not relinker_url:
            # fallback on old implementation for some old content
            try:
                return RaiIE._real_extract(self, url)
            except GeoRestrictedError:
                raise
            except ExtractorError as e:
                raise ExtractorError('Relinker URL not found', cause=e)

        relinker_info = self._extract_relinker_info(urljoin(url, relinker_url), video_id)

        return {
            'id': video_id,
            'title': player_data.get('title') or track_info.get('title') or self._og_search_title(webpage),
            'upload_date': unified_strdate(track_info.get('date')),
            'uploader': strip_or_none(track_info.get('editor') or None),
            **relinker_info
        }


class RaiCulturaIE(RaiNewsIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = rf'https?://(www\.)?raicultura\.it/(?!articoli)[^?#]+-(?P<id>{RaiBaseIE._UUID_RE})(?:-[^/?#]+)?\.html'
    _EMBED_REGEX = [rf'<iframe[^>]+data-src="(?P<url>/iframe/[^?#]+?{RaiBaseIE._UUID_RE}\.html)']
    _TESTS = [{
        'url': 'https://www.raicultura.it/letteratura/articoli/2018/12/Alberto-Asor-Rosa-Letteratura-e-potere-05ba8775-82b5-45c5-a89d-dd955fbde1fb.html',
        'info_dict': {
            'id': '05ba8775-82b5-45c5-a89d-dd955fbde1fb',
            'ext': 'mp4',
            'title': 'Alberto Asor Rosa: Letteratura e potere',
            'duration': 1756,
            'upload_date': '20181206',
            'uploader': 'raicultura',
            'formats': 'count:2',
        },
        'params': {'skip_download': True},
    }]
    _PLAYER_TAG = 'cultura'


class RaiSudtirolIE(RaiBaseIE):
    _VALID_URL = r'https?://raisudtirol\.rai\.it/.+media=(?P<id>\w+)'
    _TESTS = [{
        # mp4 file
        'url': 'https://raisudtirol.rai.it/la/index.php?media=Ptv1619729460',
        'info_dict': {
            'id': 'Ptv1619729460',
            'ext': 'mp4',
            'title': 'Euro: trasmisciun d\'economia - 29-04-2021 20:51',
            'series': 'Euro: trasmisciun d\'economia',
            'upload_date': '20210429',
            'thumbnail': r're:https://raisudtirol\.rai\.it/img/.+\.jpg',
            'uploader': 'raisudtirol',
            'formats': 'count:1',
        },
        'params': {'skip_download': True},
    }, {
        # m3u manifest
        'url': 'https://raisudtirol.rai.it/it/kidsplayer.php?lang=it&media=GUGGUG_P1.smil',
        'info_dict': {
            'id': 'GUGGUG_P1',
            'ext': 'mp4',
            'title': 'GUGGUG! La Prospettiva - Die Perspektive',
            'uploader': 'raisudtirol',
            'formats': 'count:6',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_date = self._html_search_regex(
            r'<span class="med_data">(.+?)</span>', webpage, 'video_date', default=None)
        video_title = self._html_search_regex([
            r'<span class="med_title">(.+?)</span>', r'title: \'(.+?)\','],
            webpage, 'video_title', default=None)
        video_url = self._html_search_regex([
            r'sources:\s*\[\{file:\s*"(.+?)"\}\]',
            r'<source\s+src="(.+?)"\s+type="application/x-mpegURL"'],
            webpage, 'video_url', default=None)

        ext = determine_ext(video_url)
        if ext == 'm3u8':
            formats = self._extract_m3u8_formats(video_url, video_id)
        elif ext == 'mp4':
            formats = [{
                'format_id': 'https-mp4',
                'url': self._proto_relative_url(video_url),
                'width': 1024,
                'height': 576,
                'fps': 25,
                'vcodec': 'avc1',
                'acodec': 'mp4a',
            }]
        else:
            formats = []
            self.raise_no_formats(f'Unrecognized media file: {video_url}')

        return {
            'id': video_id,
            'title': join_nonempty(video_title, video_date, delim=' - '),
            'series': video_title if video_date else None,
            'upload_date': unified_strdate(video_date),
            'thumbnail': urljoin('https://raisudtirol.rai.it/', self._html_search_regex(
                r'image: \'(.+?)\'', webpage, 'video_thumb', default=None)),
            'uploader': 'raisudtirol',
            'formats': formats,
        }
