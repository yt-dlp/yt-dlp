import functools
import re

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    bug_reports_message,
    determine_ext,
    int_or_none,
    join_nonempty,
    jwt_decode_hs256,
    make_archive_id,
    parse_duration,
    parse_iso8601,
    remove_start,
    str_or_none,
    unified_strdate,
    update_url_query,
    url_or_none,
    xpath_text,
)
from ..utils.traversal import traverse_obj


class ARDMediathekBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['DE']

    def _extract_media_info(self, media_info_url, webpage, video_id):
        media_info = self._download_json(
            media_info_url, video_id, 'Downloading media JSON')
        return self._parse_media_info(media_info, video_id, '"fsk"' in webpage)

    def _parse_media_info(self, media_info, video_id, fsk):
        formats = self._extract_formats(media_info, video_id)

        if not formats:
            if fsk:
                self.raise_no_formats(
                    'This video is only available after 20:00', expected=True)
            elif media_info.get('_geoblocked'):
                self.raise_geo_restricted(
                    'This video is not available due to geoblocking',
                    countries=self._GEO_COUNTRIES, metadata_available=True)

        subtitles = {}
        subtitle_url = media_info.get('_subtitleUrl')
        if subtitle_url:
            subtitles['de'] = [{
                'ext': 'ttml',
                'url': subtitle_url,
            }, {
                'ext': 'vtt',
                'url': subtitle_url.replace('/ebutt/', '/webvtt/') + '.vtt',
            }]

        return {
            'id': video_id,
            'duration': int_or_none(media_info.get('_duration')),
            'thumbnail': media_info.get('_previewImage'),
            'is_live': media_info.get('_isLive') is True,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _extract_formats(self, media_info, video_id):
        type_ = media_info.get('_type')
        media_array = media_info.get('_mediaArray', [])
        formats = []
        for num, media in enumerate(media_array):
            for stream in media.get('_mediaStreamArray', []):
                stream_urls = stream.get('_stream')
                if not stream_urls:
                    continue
                if not isinstance(stream_urls, list):
                    stream_urls = [stream_urls]
                quality = stream.get('_quality')
                server = stream.get('_server')
                for stream_url in stream_urls:
                    if not url_or_none(stream_url):
                        continue
                    ext = determine_ext(stream_url)
                    if quality != 'auto' and ext in ('f4m', 'm3u8'):
                        continue
                    if ext == 'f4m':
                        formats.extend(self._extract_f4m_formats(
                            update_url_query(stream_url, {
                                'hdcore': '3.1.1',
                                'plugin': 'aasp-3.1.1.69.124',
                            }), video_id, f4m_id='hds', fatal=False))
                    elif ext == 'm3u8':
                        formats.extend(self._extract_m3u8_formats(
                            stream_url, video_id, 'mp4', 'm3u8_native',
                            m3u8_id='hls', fatal=False))
                    else:
                        if server and server.startswith('rtmp'):
                            f = {
                                'url': server,
                                'play_path': stream_url,
                                'format_id': f'a{num}-rtmp-{quality}',
                            }
                        else:
                            f = {
                                'url': stream_url,
                                'format_id': f'a{num}-{ext}-{quality}',
                            }
                        m = re.search(
                            r'_(?P<width>\d+)x(?P<height>\d+)\.mp4$',
                            stream_url)
                        if m:
                            f.update({
                                'width': int(m.group('width')),
                                'height': int(m.group('height')),
                            })
                        if type_ == 'audio':
                            f['vcodec'] = 'none'
                        formats.append(f)
        return formats


class ARDIE(InfoExtractor):
    _VALID_URL = r'(?P<mainurl>https?://(?:www\.)?daserste\.de/(?:[^/?#&]+/)+(?P<id>[^/?#&]+))\.html'
    _TESTS = [{
        # available till 7.12.2023
        'url': 'https://www.daserste.de/information/talk/maischberger/videos/maischberger-video-424.html',
        'md5': '94812e6438488fb923c361a44469614b',
        'info_dict': {
            'id': 'maischberger-video-424',
            'display_id': 'maischberger-video-424',
            'ext': 'mp4',
            'duration': 4452.0,
            'title': 'maischberger am 07.12.2022',
            'upload_date': '20221207',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'https://www.daserste.de/information/politik-weltgeschehen/morgenmagazin/videosextern/dominik-kahun-aus-der-nhl-direkt-zur-weltmeisterschaft-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.daserste.de/information/nachrichten-wetter/tagesthemen/videosextern/tagesthemen-17736.html',
        'only_matching': True,
    }, {
        'url': 'https://www.daserste.de/unterhaltung/serie/in-aller-freundschaft-die-jungen-aerzte/videos/diversity-tag-sanam-afrashteh100.html',
        'only_matching': True,
    }, {
        'url': 'http://www.daserste.de/information/reportage-dokumentation/dokus/videos/die-story-im-ersten-mission-unter-falscher-flagge-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.daserste.de/unterhaltung/serie/in-aller-freundschaft-die-jungen-aerzte/Drehpause-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.daserste.de/unterhaltung/film/filmmittwoch-im-ersten/videos/making-ofwendezeit-video-100.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')

        player_url = mobj.group('mainurl') + '~playerXml.xml'
        doc = self._download_xml(player_url, display_id)
        video_node = doc.find('./video')
        upload_date = unified_strdate(xpath_text(
            video_node, './broadcastDate'))
        thumbnail = xpath_text(video_node, './/teaserImage//variant/url')

        formats = []
        for a in video_node.findall('.//asset'):
            file_name = xpath_text(a, './fileName', default=None)
            if not file_name:
                continue
            format_type = a.attrib.get('type')
            format_url = url_or_none(file_name)
            if format_url:
                ext = determine_ext(file_name)
                if ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        format_url, display_id, 'mp4', entry_protocol='m3u8_native',
                        m3u8_id=format_type or 'hls', fatal=False))
                    continue
                elif ext == 'f4m':
                    formats.extend(self._extract_f4m_formats(
                        update_url_query(format_url, {'hdcore': '3.7.0'}),
                        display_id, f4m_id=format_type or 'hds', fatal=False))
                    continue
            f = {
                'format_id': format_type,
                'width': int_or_none(xpath_text(a, './frameWidth')),
                'height': int_or_none(xpath_text(a, './frameHeight')),
                'vbr': int_or_none(xpath_text(a, './bitrateVideo')),
                'abr': int_or_none(xpath_text(a, './bitrateAudio')),
                'vcodec': xpath_text(a, './codecVideo'),
                'tbr': int_or_none(xpath_text(a, './totalBitrate')),
            }
            server_prefix = xpath_text(a, './serverPrefix', default=None)
            if server_prefix:
                f.update({
                    'url': server_prefix,
                    'playpath': file_name,
                })
            else:
                if not format_url:
                    continue
                f['url'] = format_url
            formats.append(f)

        _SUB_FORMATS = (
            ('./dataTimedText', 'ttml'),
            ('./dataTimedTextNoOffset', 'ttml'),
            ('./dataTimedTextVtt', 'vtt'),
        )

        subtitles = {}
        for subsel, subext in _SUB_FORMATS:
            for node in video_node.findall(subsel):
                subtitles.setdefault('de', []).append({
                    'url': node.attrib['url'],
                    'ext': subext,
                })

        return {
            'id': xpath_text(video_node, './videoId', default=display_id),
            'formats': formats,
            'subtitles': subtitles,
            'display_id': display_id,
            'title': video_node.find('./title').text,
            'duration': parse_duration(video_node.find('./duration').text),
            'upload_date': upload_date,
            'thumbnail': thumbnail,
        }


class ARDBetaMediathekIE(InfoExtractor):
    IE_NAME = 'ARDMediathek'
    _VALID_URL = r'''(?x)https?://
        (?:(?:beta|www)\.)?ardmediathek\.de/
        (?:[^/]+/)?
        (?:player|live|video)/
        (?:[^?#]+/)?
        (?P<id>[a-zA-Z0-9]+)
        /?(?:[?#]|$)'''
    _GEO_COUNTRIES = ['DE']
    _TOKEN_URL = 'https://sso.ardmediathek.de/sso/token'

    _TESTS = [{
        'url': 'https://www.ardmediathek.de/video/filme-im-mdr/liebe-auf-vier-pfoten/mdr-fernsehen/Y3JpZDovL21kci5kZS9zZW5kdW5nLzI4MjA0MC80MjIwOTEtNDAyNTM0',
        'md5': 'b6e8ab03f2bcc6e1f9e6cef25fcc03c4',
        'info_dict': {
            'display_id': 'Y3JpZDovL21kci5kZS9zZW5kdW5nLzI4MjA0MC80MjIwOTEtNDAyNTM0',
            'id': '12939099',
            'title': 'Liebe auf vier Pfoten',
            'description': r're:^Claudia Schmitt, Anwältin in Salzburg',
            'duration': 5222,
            'thumbnail': 'https://api.ardmediathek.de/image-service/images/urn:ard:image:aee7cbf8f06de976?w=960&ch=ae4d0f2ee47d8b9b',
            'timestamp': 1701343800,
            'upload_date': '20231130',
            'ext': 'mp4',
            'episode': 'Liebe auf vier Pfoten',
            'series': 'Filme im MDR',
            'age_limit': 0,
            'channel': 'MDR',
            '_old_archive_ids': ['ardbetamediathek Y3JpZDovL21kci5kZS9zZW5kdW5nLzI4MjA0MC80MjIwOTEtNDAyNTM0'],
        },
    }, {
        'url': 'https://www.ardmediathek.de/mdr/video/die-robuste-roswita/Y3JpZDovL21kci5kZS9iZWl0cmFnL2Ntcy84MWMxN2MzZC0wMjkxLTRmMzUtODk4ZS0wYzhlOWQxODE2NGI/',
        'md5': 'a1dc75a39c61601b980648f7c9f9f71d',
        'info_dict': {
            'display_id': 'die-robuste-roswita',
            'id': '78566716',
            'title': 'Die robuste Roswita',
            'description': r're:^Der Mord.*totgeglaubte Ehefrau Roswita',
            'duration': 5316,
            'thumbnail': 'https://img.ardmediathek.de/standard/00/78/56/67/84/575672121/16x9/960?mandant=ard',
            'timestamp': 1596658200,
            'upload_date': '20200805',
            'ext': 'mp4',
        },
        'skip': 'Error',
    }, {
        'url': 'https://www.ardmediathek.de/video/tagesschau-oder-tagesschau-20-00-uhr/das-erste/Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhZ2Vzc2NoYXUvZmM4ZDUxMjgtOTE0ZC00Y2MzLTgzNzAtNDZkNGNiZWJkOTll',
        'md5': '1e73ded21cb79bac065117e80c81dc88',
        'info_dict': {
            'id': '10049223',
            'ext': 'mp4',
            'title': 'tagesschau, 20:00 Uhr',
            'timestamp': 1636398000,
            'description': 'md5:39578c7b96c9fe50afdf5674ad985e6b',
            'upload_date': '20211108',
            'display_id': 'Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhZ2Vzc2NoYXUvZmM4ZDUxMjgtOTE0ZC00Y2MzLTgzNzAtNDZkNGNiZWJkOTll',
            'duration': 915,
            'episode': 'tagesschau, 20:00 Uhr',
            'series': 'tagesschau',
            'thumbnail': 'https://api.ardmediathek.de/image-service/images/urn:ard:image:fbb21142783b0a49?w=960&ch=ee69108ae344f678',
            'channel': 'ARD-Aktuell',
            '_old_archive_ids': ['ardbetamediathek Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhZ2Vzc2NoYXUvZmM4ZDUxMjgtOTE0ZC00Y2MzLTgzNzAtNDZkNGNiZWJkOTll'],
        },
    }, {
        'url': 'https://www.ardmediathek.de/video/7-tage/7-tage-unter-harten-jungs/hr-fernsehen/N2I2YmM5MzgtNWFlOS00ZGFlLTg2NzMtYzNjM2JlNjk4MDg3',
        'md5': 'c428b9effff18ff624d4f903bda26315',
        'info_dict': {
            'id': '94834686',
            'ext': 'mp4',
            'duration': 2700,
            'episode': '7 Tage ... unter harten Jungs',
            'description': 'md5:0f215470dcd2b02f59f4bd10c963f072',
            'upload_date': '20231005',
            'timestamp': 1696491171,
            'display_id': 'N2I2YmM5MzgtNWFlOS00ZGFlLTg2NzMtYzNjM2JlNjk4MDg3',
            'series': '7 Tage ...',
            'channel': 'HR',
            'thumbnail': 'https://api.ardmediathek.de/image-service/images/urn:ard:image:f6e6d5ffac41925c?w=960&ch=fa32ba69bc87989a',
            'title': '7 Tage ... unter harten Jungs',
            '_old_archive_ids': ['ardbetamediathek N2I2YmM5MzgtNWFlOS00ZGFlLTg2NzMtYzNjM2JlNjk4MDg3'],
        },
    }, {
        'url': 'https://beta.ardmediathek.de/ard/video/Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhdG9ydC9mYmM4NGM1NC0xNzU4LTRmZGYtYWFhZS0wYzcyZTIxNGEyMDE',
        'only_matching': True,
    }, {
        'url': 'https://ardmediathek.de/ard/video/saartalk/saartalk-gesellschaftsgift-haltung-gegen-hass/sr-fernsehen/Y3JpZDovL3NyLW9ubGluZS5kZS9TVF84MTY4MA/',
        'only_matching': True,
    }, {
        'url': 'https://www.ardmediathek.de/ard/video/trailer/private-eyes-s01-e01/one/Y3JpZDovL3dkci5kZS9CZWl0cmFnLTE1MTgwYzczLWNiMTEtNGNkMS1iMjUyLTg5MGYzOWQxZmQ1YQ/',
        'only_matching': True,
    }, {
        'url': 'https://www.ardmediathek.de/ard/player/Y3JpZDovL3N3ci5kZS9hZXgvbzEwNzE5MTU/',
        'only_matching': True,
    }, {
        'url': 'https://www.ardmediathek.de/swr/live/Y3JpZDovL3N3ci5kZS8xMzQ4MTA0Mg',
        'only_matching': True,
    }, {
        'url': 'https://www.ardmediathek.de/video/coronavirus-update-ndr-info/astrazeneca-kurz-lockdown-und-pims-syndrom-81/ndr/Y3JpZDovL25kci5kZS84NzE0M2FjNi0wMWEwLTQ5ODEtOTE5NS1mOGZhNzdhOTFmOTI/',
        'only_matching': True,
    }]

    def _extract_episode_info(self, title):
        patterns = [
            # Pattern for title like "Homo sapiens (S06/E07) - Originalversion"
            # from: https://www.ardmediathek.de/one/sendung/doctor-who/Y3JpZDovL3dkci5kZS9vbmUvZG9jdG9yIHdobw
            r'.*(?P<ep_info> \(S(?P<season_number>\d+)/E(?P<episode_number>\d+)\)).*',
            # E.g.: title="Fritjof aus Norwegen (2) (AD)"
            # from: https://www.ardmediathek.de/ard/sammlung/der-krieg-und-ich/68cMkqJdllm639Skj4c7sS/
            r'.*(?P<ep_info> \((?:Folge |Teil )?(?P<episode_number>\d+)(?:/\d+)?\)).*',
            r'.*(?P<ep_info>Folge (?P<episode_number>\d+)(?:\:| -|) )\"(?P<episode>.+)\".*',
            # E.g.: title="Folge 25/42: Symmetrie"
            # from: https://www.ardmediathek.de/ard/video/grips-mathe/folge-25-42-symmetrie/ard-alpha/Y3JpZDovL2JyLmRlL3ZpZGVvLzMyYzI0ZjczLWQ1N2MtNDAxNC05ZmZhLTFjYzRkZDA5NDU5OQ/
            # E.g.: title="Folge 1063 - Vertrauen"
            # from: https://www.ardmediathek.de/ard/sendung/die-fallers/Y3JpZDovL3N3ci5kZS8yMzAyMDQ4/
            r'.*(?P<ep_info>Folge (?P<episode_number>\d+)(?:/\d+)?(?:\:| -|) ).*',
            # As a fallback use the full title
            r'(?P<title>.*)',
        ]

        return traverse_obj(patterns, (..., {functools.partial(re.match, string=title)}, {
            'season_number': ('season_number', {int_or_none}),
            'episode_number': ('episode_number', {int_or_none}),
            'episode': ((
                ('episode', {str_or_none}),
                ('ep_info', {lambda x: title.replace(x, '')}),
                ('title', {str}),
            ), {str.strip}),
        }), get_all=False)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        query = {'embedded': 'false', 'mcV6': 'true'}
        headers = {}

        if self._get_cookies(self._TOKEN_URL).get('ams'):
            token = self._download_json(
                self._TOKEN_URL, display_id, 'Fetching token for age verification',
                'Unable to fetch age verification token', fatal=False)
            id_token = traverse_obj(token, ('idToken', {str}))
            decoded_token = traverse_obj(id_token, ({jwt_decode_hs256}, {dict}))
            user_id = traverse_obj(decoded_token, (('user_id', 'sub'), {str}), get_all=False)
            if not user_id:
                self.report_warning('Unable to extract token, continuing without authentication')
            else:
                headers['x-authorization'] = f'Bearer {id_token}'
                query['userId'] = user_id
                if decoded_token.get('age_rating') != 18:
                    self.report_warning('Account is not verified as 18+; video may be unavailable')

        page_data = self._download_json(
            f'https://api.ardmediathek.de/page-gateway/pages/ard/item/{display_id}',
            display_id, query=query, headers=headers)

        # For user convenience we use the old contentId instead of the longer crid
        # Ref: https://github.com/yt-dlp/yt-dlp/issues/8731#issuecomment-1874398283
        old_id = traverse_obj(page_data, ('tracking', 'atiCustomVars', 'contentId', {int}))
        if old_id is not None:
            video_id = str(old_id)
            archive_ids = [make_archive_id(ARDBetaMediathekIE, display_id)]
        else:
            self.report_warning(f'Could not extract contentId{bug_reports_message()}')
            video_id = display_id
            archive_ids = None

        player_data = traverse_obj(
            page_data, ('widgets', lambda _, v: v['type'] in ('player_ondemand', 'player_live'), {dict}), get_all=False)
        is_live = player_data.get('type') == 'player_live'
        media_data = traverse_obj(player_data, ('mediaCollection', 'embedded', {dict}))

        if player_data.get('blockedByFsk'):
            self.raise_login_required('This video is only available for age verified users or after 22:00')

        formats = []
        subtitles = {}
        for stream in traverse_obj(media_data, ('streams', ..., {dict})):
            kind = stream.get('kind')
            # Prioritize main stream over sign language and others
            preference = 1 if kind == 'main' else None
            for media in traverse_obj(stream, ('media', lambda _, v: url_or_none(v['url']))):
                media_url = media['url']

                audio_kind = traverse_obj(media, (
                    'audios', 0, 'kind', {str}), default='').replace('standard', '')
                lang_code = traverse_obj(media, ('audios', 0, 'languageCode', {str})) or 'deu'
                lang = join_nonempty(lang_code, audio_kind)
                language_preference = 10 if lang == 'deu' else -10

                if determine_ext(media_url) == 'm3u8':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        media_url, video_id, m3u8_id=f'hls-{kind}', preference=preference, fatal=False, live=is_live)
                    for f in fmts:
                        f['language'] = lang
                        f['language_preference'] = language_preference
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                else:
                    formats.append({
                        'url': media_url,
                        'format_id': f'http-{kind}',
                        'preference': preference,
                        'language': lang,
                        'language_preference': language_preference,
                        **traverse_obj(media, {
                            'format_note': ('forcedLabel', {str}),
                            'width': ('maxHResolutionPx', {int_or_none}),
                            'height': ('maxVResolutionPx', {int_or_none}),
                            'vcodec': ('videoCodec', {str}),
                        }),
                    })

        for sub in traverse_obj(media_data, ('subtitles', ..., {dict})):
            for sources in traverse_obj(sub, ('sources', lambda _, v: url_or_none(v['url']))):
                subtitles.setdefault(sub.get('languageCode') or 'deu', []).append({
                    'url': sources['url'],
                    'ext': {'webvtt': 'vtt', 'ebutt': 'ttml'}.get(sources.get('kind')),
                })

        age_limit = traverse_obj(page_data, ('fskRating', {lambda x: remove_start(x, 'FSK')}, {int_or_none}))
        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
            'age_limit': age_limit,
            **traverse_obj(media_data, ('meta', {
                'title': 'title',
                'description': 'synopsis',
                'timestamp': ('broadcastedOnDateTime', {parse_iso8601}),
                'series': 'seriesTitle',
                'thumbnail': ('images', 0, 'url', {url_or_none}),
                'duration': ('durationSeconds', {int_or_none}),
                'channel': 'clipSourceName',
            })),
            **self._extract_episode_info(page_data.get('title')),
            '_old_archive_ids': archive_ids,
        }


class ARDMediathekCollectionIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://
        (?:(?:beta|www)\.)?ardmediathek\.de/
        (?:[^/?#]+/)?
        (?P<playlist>sendung|serie|sammlung)/
        (?:(?P<display_id>[^?#]+?)/)?
        (?P<id>[a-zA-Z0-9]+)
        (?:/(?P<season>\d+)(?:/(?P<version>OV|AD))?)?/?(?:[?#]|$)'''
    _GEO_COUNTRIES = ['DE']

    _TESTS = [{
        'url': 'https://www.ardmediathek.de/serie/quiz/staffel-1-originalversion/Y3JpZDovL3dkci5kZS9vbmUvcXVpeg/1/OV',
        'info_dict': {
            'id': 'Y3JpZDovL3dkci5kZS9vbmUvcXVpeg_1_OV',
            'display_id': 'quiz/staffel-1-originalversion',
            'title': 'Staffel 1 Originalversion',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://www.ardmediathek.de/serie/babylon-berlin/staffel-4-mit-audiodeskription/Y3JpZDovL2Rhc2Vyc3RlLmRlL2JhYnlsb24tYmVybGlu/4/AD',
        'info_dict': {
            'id': 'Y3JpZDovL2Rhc2Vyc3RlLmRlL2JhYnlsb24tYmVybGlu_4_AD',
            'display_id': 'babylon-berlin/staffel-4-mit-audiodeskription',
            'title': 'Staffel 4 mit Audiodeskription',
        },
        'playlist_count': 12,
    }, {
        'url': 'https://www.ardmediathek.de/serie/babylon-berlin/staffel-1/Y3JpZDovL2Rhc2Vyc3RlLmRlL2JhYnlsb24tYmVybGlu/1/',
        'info_dict': {
            'id': 'Y3JpZDovL2Rhc2Vyc3RlLmRlL2JhYnlsb24tYmVybGlu_1',
            'display_id': 'babylon-berlin/staffel-1',
            'title': 'Staffel 1',
        },
        'playlist_count': 8,
    }, {
        'url': 'https://www.ardmediathek.de/sendung/tatort/Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhdG9ydA',
        'info_dict': {
            'id': 'Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhdG9ydA',
            'display_id': 'tatort',
            'title': 'Tatort',
        },
        'playlist_mincount': 500,
    }, {
        'url': 'https://www.ardmediathek.de/sammlung/die-kirche-bleibt-im-dorf/5eOHzt8XB2sqeFXbIoJlg2',
        'info_dict': {
            'id': '5eOHzt8XB2sqeFXbIoJlg2',
            'display_id': 'die-kirche-bleibt-im-dorf',
            'title': 'Die Kirche bleibt im Dorf',
            'description': 'Die Kirche bleibt im Dorf',
        },
        'playlist_count': 4,
    }, {
        # playlist of type 'sendung'
        'url': 'https://www.ardmediathek.de/ard/sendung/doctor-who/Y3JpZDovL3dkci5kZS9vbmUvZG9jdG9yIHdobw/',
        'only_matching': True,
    }, {
        # playlist of type 'serie'
        'url': 'https://www.ardmediathek.de/serie/nachtstreife/staffel-1/Y3JpZDovL3N3ci5kZS9zZGIvc3RJZC8xMjQy/1',
        'only_matching': True,
    }, {
        # playlist of type 'sammlung'
        'url': 'https://www.ardmediathek.de/ard/sammlung/team-muenster/5JpTzLSbWUAK8184IOvEir/',
        'only_matching': True,
    }]

    _PAGE_SIZE = 100

    def _real_extract(self, url):
        playlist_id, display_id, playlist_type, season_number, version = self._match_valid_url(url).group(
            'id', 'display_id', 'playlist', 'season', 'version')

        def call_api(page_num):
            api_path = 'compilations/ard' if playlist_type == 'sammlung' else 'widgets/ard/asset'
            return self._download_json(
                f'https://api.ardmediathek.de/page-gateway/{api_path}/{playlist_id}', playlist_id,
                f'Downloading playlist page {page_num}', query={
                    'pageNumber': page_num,
                    'pageSize': self._PAGE_SIZE,
                    **({
                        'seasoned': 'true',
                        'seasonNumber': season_number,
                        'withOriginalversion': 'true' if version == 'OV' else 'false',
                        'withAudiodescription': 'true' if version == 'AD' else 'false',
                    } if season_number else {}),
                })

        def fetch_page(page_num):
            for item in traverse_obj(call_api(page_num), ('teasers', ..., {dict})):
                item_id = traverse_obj(item, ('links', 'target', ('urlId', 'id')), 'id', get_all=False)
                if not item_id or item_id == playlist_id:
                    continue
                item_mode = 'sammlung' if item.get('type') == 'compilation' else 'video'
                yield self.url_result(
                    f'https://www.ardmediathek.de/{item_mode}/{item_id}',
                    ie=(ARDMediathekCollectionIE if item_mode == 'sammlung' else ARDBetaMediathekIE),
                    **traverse_obj(item, {
                        'id': ('id', {str}),
                        'title': ('longTitle', {str}),
                        'duration': ('duration', {int_or_none}),
                        'timestamp': ('broadcastedOn', {parse_iso8601}),
                    }))

        page_data = call_api(0)
        full_id = join_nonempty(playlist_id, season_number, version, delim='_')

        return self.playlist_result(
            OnDemandPagedList(fetch_page, self._PAGE_SIZE), full_id, display_id=display_id,
            title=page_data.get('title'), description=page_data.get('synopsis'))
