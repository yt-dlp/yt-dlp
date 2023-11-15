import json
import re

from .common import InfoExtractor
from .generic import GenericIE
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    parse_duration,
    qualities,
    str_or_none,
    try_get,
    unified_strdate,
    unified_timestamp,
    update_url,
    update_url_query,
    url_or_none,
    xpath_text,
)
from ..compat import compat_etree_fromstring


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

    def _ARD_extract_episode_info(self, title):
        """Try to extract season/episode data from the title."""
        res = {}
        if not title:
            return res

        for pattern in [
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
        ]:
            m = re.match(pattern, title)
            if m:
                groupdict = m.groupdict()
                res['season_number'] = int_or_none(groupdict.get('season_number'))
                res['episode_number'] = int_or_none(groupdict.get('episode_number'))
                res['episode'] = str_or_none(groupdict.get('episode'))
                # Build the episode title by removing numeric episode information:
                if groupdict.get('ep_info') and not res['episode']:
                    res['episode'] = str_or_none(
                        title.replace(groupdict.get('ep_info'), ''))
                if res['episode']:
                    res['episode'] = res['episode'].strip()
                break

        # As a fallback use the whole title as the episode name:
        if not res.get('episode'):
            res['episode'] = title.strip()
        return res

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
                                'plugin': 'aasp-3.1.1.69.124'
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
                                'format_id': 'a%s-rtmp-%s' % (num, quality),
                            }
                        else:
                            f = {
                                'url': stream_url,
                                'format_id': 'a%s-%s-%s' % (num, ext, quality)
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


class ARDMediathekIE(ARDMediathekBaseIE):
    IE_NAME = 'ARD:mediathek'
    _VALID_URL = r'^https?://(?:(?:(?:www|classic)\.)?ardmediathek\.de|mediathek\.(?:daserste|rbb-online)\.de|one\.ard\.de)/(?:.*/)(?P<video_id>[0-9]+|[^0-9][^/\?]+)[^/\?]*(?:\?.*)?'

    _TESTS = [{
        # available till 26.07.2022
        'url': 'http://www.ardmediathek.de/tv/S%C3%9CDLICHT/Was-ist-die-Kunst-der-Zukunft-liebe-Ann/BR-Fernsehen/Video?bcastId=34633636&documentId=44726822',
        'info_dict': {
            'id': '44726822',
            'ext': 'mp4',
            'title': 'Was ist die Kunst der Zukunft, liebe Anna McCarthy?',
            'description': 'md5:4ada28b3e3b5df01647310e41f3a62f5',
            'duration': 1740,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }, {
        'url': 'https://one.ard.de/tv/Mord-mit-Aussicht/Mord-mit-Aussicht-6-39-T%C3%B6dliche-Nach/ONE/Video?bcastId=46384294&documentId=55586872',
        'only_matching': True,
    }, {
        # audio
        'url': 'http://www.ardmediathek.de/tv/WDR-H%C3%B6rspiel-Speicher/Tod-eines-Fu%C3%9Fballers/WDR-3/Audio-Podcast?documentId=28488308&bcastId=23074086',
        'only_matching': True,
    }, {
        'url': 'http://mediathek.daserste.de/sendungen_a-z/328454_anne-will/22429276_vertrauen-ist-gut-spionieren-ist-besser-geht',
        'only_matching': True,
    }, {
        # audio
        'url': 'http://mediathek.rbb-online.de/radio/Hörspiel/Vor-dem-Fest/kulturradio/Audio?documentId=30796318&topRessort=radio&bcastId=9839158',
        'only_matching': True,
    }, {
        'url': 'https://classic.ardmediathek.de/tv/Panda-Gorilla-Co/Panda-Gorilla-Co-Folge-274/Das-Erste/Video?bcastId=16355486&documentId=58234698',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if ARDBetaMediathekIE.suitable(url) else super(ARDMediathekIE, cls).suitable(url)

    def _real_extract(self, url):
        # determine video id from url
        m = self._match_valid_url(url)

        document_id = None

        numid = re.search(r'documentId=([0-9]+)', url)
        if numid:
            document_id = video_id = numid.group(1)
        else:
            video_id = m.group('video_id')

        webpage = self._download_webpage(url, video_id)

        ERRORS = (
            ('>Leider liegt eine Störung vor.', 'Video %s is unavailable'),
            ('>Der gewünschte Beitrag ist nicht mehr verfügbar.<',
             'Video %s is no longer available'),
        )

        for pattern, message in ERRORS:
            if pattern in webpage:
                raise ExtractorError(message % video_id, expected=True)

        if re.search(r'[\?&]rss($|[=&])', url):
            doc = compat_etree_fromstring(webpage.encode('utf-8'))
            if doc.tag == 'rss':
                return GenericIE()._extract_rss(url, video_id, doc)

        title = self._og_search_title(webpage, default=None) or self._html_search_regex(
            [r'<h1(?:\s+class="boxTopHeadline")?>(.*?)</h1>',
             r'<meta name="dcterms\.title" content="(.*?)"/>',
             r'<h4 class="headline">(.*?)</h4>',
             r'<title[^>]*>(.*?)</title>'],
            webpage, 'title')
        description = self._og_search_description(webpage, default=None) or self._html_search_meta(
            'dcterms.abstract', webpage, 'description', default=None)
        if description is None:
            description = self._html_search_meta(
                'description', webpage, 'meta description', default=None)
        if description is None:
            description = self._html_search_regex(
                r'<p\s+class="teasertext">(.+?)</p>',
                webpage, 'teaser text', default=None)

        # Thumbnail is sometimes not present.
        # It is in the mobile version, but that seems to use a different URL
        # structure altogether.
        thumbnail = self._og_search_thumbnail(webpage, default=None)

        media_streams = re.findall(r'''(?x)
            mediaCollection\.addMediaStream\([0-9]+,\s*[0-9]+,\s*"[^"]*",\s*
            "([^"]+)"''', webpage)

        if media_streams:
            QUALITIES = qualities(['lo', 'hi', 'hq'])
            formats = []
            for furl in set(media_streams):
                if furl.endswith('.f4m'):
                    fid = 'f4m'
                else:
                    fid_m = re.match(r'.*\.([^.]+)\.[^.]+$', furl)
                    fid = fid_m.group(1) if fid_m else None
                formats.append({
                    'quality': QUALITIES(fid),
                    'format_id': fid,
                    'url': furl,
                })
            info = {
                'formats': formats,
            }
        else:  # request JSON file
            if not document_id:
                video_id = self._search_regex(
                    (r'/play/(?:config|media|sola)/(\d+)', r'contentId["\']\s*:\s*(\d+)'),
                    webpage, 'media id', default=None)
            info = self._extract_media_info(
                'http://www.ardmediathek.de/play/media/%s' % video_id,
                webpage, video_id)

        info.update({
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
        })
        info.update(self._ARD_extract_episode_info(info['title']))

        return info


class ARDIE(InfoExtractor):
    _VALID_URL = r'(?P<mainurl>https?://(?:www\.)?daserste\.de/(?:[^/?#&]+/)+(?P<id>[^/?#&]+))\.html'
    _TESTS = [{
        # available till 7.12.2023
        'url': 'https://www.daserste.de/information/talk/maischberger/videos/maischberger-video-424.html',
        'md5': 'a438f671e87a7eba04000336a119ccc4',
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


class ARDBetaMediathekIE(ARDMediathekBaseIE):
    _VALID_URL = r'''(?x)https://
        (?:(?:beta|www)\.)?ardmediathek\.de/
        (?:(?P<client>[^/]+)/)?
        (?:player|live|video|(?P<playlist>sendung|sammlung))/
        (?:(?P<display_id>(?(playlist)[^?#]+?|[^?#]+))/)?
        (?P<id>(?(playlist)|Y3JpZDovL)[a-zA-Z0-9]+)
        (?(playlist)/(?P<season>\d+)?/?(?:[?#]|$))'''

    _TESTS = [{
        'url': 'https://www.ardmediathek.de/video/filme-im-mdr/wolfsland-die-traurigen-schwestern/mdr-fernsehen/Y3JpZDovL21kci5kZS9iZWl0cmFnL2Ntcy8xZGY0ZGJmZS00ZWQwLTRmMGItYjhhYy0wOGQ4ZmYxNjVhZDI',
        'md5': '3fd5fead7a370a819341129c8d713136',
        'info_dict': {
            'display_id': 'filme-im-mdr/wolfsland-die-traurigen-schwestern/mdr-fernsehen',
            'id': '12172961',
            'title': 'Wolfsland - Die traurigen Schwestern',
            'description': r're:^Als der Polizeiobermeister Raaben',
            'duration': 5241,
            'thumbnail': 'https://api.ardmediathek.de/image-service/images/urn:ard:image:efa186f7b0054957',
            'timestamp': 1670710500,
            'upload_date': '20221210',
            'ext': 'mp4',
            'age_limit': 12,
            'episode': 'Wolfsland - Die traurigen Schwestern',
            'series': 'Filme im MDR'
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
            'display_id': 'tagesschau-oder-tagesschau-20-00-uhr/das-erste',
            'duration': 915,
            'episode': 'tagesschau, 20:00 Uhr',
            'series': 'tagesschau',
            'thumbnail': 'https://api.ardmediathek.de/image-service/images/urn:ard:image:fbb21142783b0a49',
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
        # playlist of type 'sendung'
        'url': 'https://www.ardmediathek.de/ard/sendung/doctor-who/Y3JpZDovL3dkci5kZS9vbmUvZG9jdG9yIHdobw/',
        'only_matching': True,
    }, {
        # playlist of type 'sammlung'
        'url': 'https://www.ardmediathek.de/ard/sammlung/team-muenster/5JpTzLSbWUAK8184IOvEir/',
        'only_matching': True,
    }, {
        'url': 'https://www.ardmediathek.de/video/coronavirus-update-ndr-info/astrazeneca-kurz-lockdown-und-pims-syndrom-81/ndr/Y3JpZDovL25kci5kZS84NzE0M2FjNi0wMWEwLTQ5ODEtOTE5NS1mOGZhNzdhOTFmOTI/',
        'only_matching': True,
    }, {
        'url': 'https://www.ardmediathek.de/ard/player/Y3JpZDovL3dkci5kZS9CZWl0cmFnLWQ2NDJjYWEzLTMwZWYtNGI4NS1iMTI2LTU1N2UxYTcxOGIzOQ/tatort-duo-koeln-leipzig-ihr-kinderlein-kommet',
        'only_matching': True,
    }]

    def _ARD_load_playlist_snipped(self, playlist_id, display_id, client, mode, pageNumber):
        """ Query the ARD server for playlist information
        and returns the data in "raw" format """
        if mode == 'sendung':
            graphQL = json.dumps({
                'query': '''{
                    showPage(
                        client: "%s"
                        showId: "%s"
                        pageNumber: %d
                    ) {
                        pagination {
                            pageSize
                            totalElements
                        }
                        teasers {        # Array
                            mediumTitle
                            links { target { id href title } }
                            type
                        }
                    }}''' % (client, playlist_id, pageNumber),
            }).encode()
        else:  # mode == 'sammlung'
            graphQL = json.dumps({
                'query': '''{
                    morePage(
                        client: "%s"
                        compilationId: "%s"
                        pageNumber: %d
                    ) {
                        widget {
                            pagination {
                                pageSize
                                totalElements
                            }
                            teasers {        # Array
                                mediumTitle
                                links { target { id href title } }
                                type
                            }
                        }
                    }}''' % (client, playlist_id, pageNumber),
            }).encode()
        # Ressources for ARD graphQL debugging:
        # https://api-test.ardmediathek.de/public-gateway
        show_page = self._download_json(
            'https://api.ardmediathek.de/public-gateway',
            '[Playlist] %s' % display_id,
            data=graphQL,
            headers={'Content-Type': 'application/json'})['data']
        # align the structure of the returned data:
        if mode == 'sendung':
            show_page = show_page['showPage']
        else:  # mode == 'sammlung'
            show_page = show_page['morePage']['widget']
        return show_page

    def _ARD_extract_playlist(self, url, playlist_id, display_id, client, mode):
        """ Collects all playlist entries and returns them as info dict.
        Supports playlists of mode 'sendung' and 'sammlung', and also nested
        playlists. """
        entries = []
        pageNumber = 0
        while True:  # iterate by pageNumber
            show_page = self._ARD_load_playlist_snipped(
                playlist_id, display_id, client, mode, pageNumber)
            for teaser in show_page['teasers']:  # process playlist items
                if '/compilation/' in teaser['links']['target']['href']:
                    # alternativ cond.: teaser['type'] == "compilation"
                    # => This is an nested compilation, e.g. like:
                    # https://www.ardmediathek.de/ard/sammlung/die-kirche-bleibt-im-dorf/5eOHzt8XB2sqeFXbIoJlg2/
                    link_mode = 'sammlung'
                else:
                    link_mode = 'video'

                item_url = 'https://www.ardmediathek.de/%s/%s/%s/%s/%s' % (
                    client, link_mode, display_id,
                    # perform HTLM quoting of episode title similar to ARD:
                    re.sub('^-|-$', '',  # remove '-' from begin/end
                           re.sub('[^a-zA-Z0-9]+', '-',  # replace special chars by -
                                  teaser['links']['target']['title'].lower()
                                  .replace('ä', 'ae').replace('ö', 'oe')
                                  .replace('ü', 'ue').replace('ß', 'ss'))),
                    teaser['links']['target']['id'])
                entries.append(self.url_result(
                    item_url,
                    ie=ARDBetaMediathekIE.ie_key()))

            if (show_page['pagination']['pageSize'] * (pageNumber + 1)
               >= show_page['pagination']['totalElements']):
                # we've processed enough pages to get all playlist entries
                break
            pageNumber = pageNumber + 1

        return self.playlist_result(entries, playlist_id, playlist_title=display_id)

    def _real_extract(self, url):
        video_id, display_id, playlist_type, client, season_number = self._match_valid_url(url).group(
            'id', 'display_id', 'playlist', 'client', 'season')
        display_id, client = display_id or video_id, client or 'ard'

        if playlist_type:
            # TODO: Extract only specified season
            return self._ARD_extract_playlist(url, video_id, display_id, client, playlist_type)

        player_page = self._download_json(
            'https://api.ardmediathek.de/public-gateway',
            display_id, data=json.dumps({
                'query': '''{
  playerPage(client:"%s", clipId: "%s") {
    blockedByFsk
    broadcastedOn
    maturityContentRating
    mediaCollection {
      _duration
      _geoblocked
      _isLive
      _mediaArray {
        _mediaStreamArray {
          _quality
          _server
          _stream
        }
      }
      _previewImage
      _subtitleUrl
      _type
    }
    show {
      title
    }
    image {
      src
    }
    synopsis
    title
    tracking {
      atiCustomVars {
        contentId
      }
    }
  }
}''' % (client, video_id),
            }).encode(), headers={
                'Content-Type': 'application/json'
            })['data']['playerPage']
        title = player_page['title']
        content_id = str_or_none(try_get(
            player_page, lambda x: x['tracking']['atiCustomVars']['contentId']))
        media_collection = player_page.get('mediaCollection') or {}
        if not media_collection and content_id:
            media_collection = self._download_json(
                'https://www.ardmediathek.de/play/media/' + content_id,
                content_id, fatal=False) or {}
        info = self._parse_media_info(
            media_collection, content_id or video_id,
            player_page.get('blockedByFsk'))
        age_limit = None
        description = player_page.get('synopsis')
        maturity_content_rating = player_page.get('maturityContentRating')
        if maturity_content_rating:
            age_limit = int_or_none(maturity_content_rating.lstrip('FSK'))
        if not age_limit and description:
            age_limit = int_or_none(self._search_regex(
                r'\(FSK\s*(\d+)\)\s*$', description, 'age limit', default=None))
        info.update({
            'age_limit': age_limit,
            'display_id': display_id,
            'title': title,
            'description': description,
            'timestamp': unified_timestamp(player_page.get('broadcastedOn')),
            'series': try_get(player_page, lambda x: x['show']['title']),
            'thumbnail': (media_collection.get('_previewImage')
                          or try_get(player_page, lambda x: update_url(x['image']['src'], query=None, fragment=None))
                          or self.get_thumbnail_from_html(display_id, url)),
        })
        info.update(self._ARD_extract_episode_info(info['title']))
        return info

    def get_thumbnail_from_html(self, display_id, url):
        webpage = self._download_webpage(url, display_id, fatal=False) or ''
        return (
            self._og_search_thumbnail(webpage, default=None)
            or self._html_search_meta('thumbnailUrl', webpage, default=None))
