# coding: utf-8
from __future__ import unicode_literals

import functools
import itertools
import json
import re

from .common import InfoExtractor
from ..compat import (
    compat_etree_Element,
    compat_HTTPError,
    compat_parse_qs,
    compat_urllib_parse_urlparse,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    dict_get,
    float_or_none,
    get_element_by_class,
    int_or_none,
    js_to_json,
    parse_duration,
    parse_iso8601,
    try_get,
    unescapeHTML,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class BBCCoUkIE(InfoExtractor):
    IE_NAME = 'bbc.co.uk'
    IE_DESC = 'BBC iPlayer'
    _ID_REGEX = r'(?:[pbm][\da-z]{7}|w[\da-z]{7,14})'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?bbc\.co\.uk/
                        (?:
                            programmes/(?!articles/)|
                            iplayer(?:/[^/]+)?/(?:episode/|playlist/)|
                            music/(?:clips|audiovideo/popular)[/#]|
                            radio/player/|
                            sounds/play/|
                            events/[^/]+/play/[^/]+/
                        )
                        (?P<id>%s)(?!/(?:episodes|broadcasts|clips))
                    ''' % _ID_REGEX

    _LOGIN_URL = 'https://account.bbc.com/signin'
    _NETRC_MACHINE = 'bbc'

    _MEDIA_SELECTOR_URL_TEMPL = 'https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/%s/vpid/%s'
    _MEDIA_SETS = [
        # Provides HQ HLS streams with even better quality that pc mediaset but fails
        # with geolocation in some cases when it's even not geo restricted at all (e.g.
        # http://www.bbc.co.uk/programmes/b06bp7lf). Also may fail with selectionunavailable.
        'iptv-all',
        'pc',
    ]

    _EMP_PLAYLIST_NS = 'http://bbc.co.uk/2008/emp/playlist'

    _TESTS = [
        {
            'url': 'http://www.bbc.co.uk/programmes/b039g8p7',
            'info_dict': {
                'id': 'b039d07m',
                'ext': 'flv',
                'title': 'Kaleidoscope, Leonard Cohen',
                'description': 'The Canadian poet and songwriter reflects on his musical career.',
            },
            'params': {
                # rtmp download
                'skip_download': True,
            }
        },
        {
            'url': 'http://www.bbc.co.uk/iplayer/episode/b00yng5w/The_Man_in_Black_Series_3_The_Printed_Name/',
            'info_dict': {
                'id': 'b00yng1d',
                'ext': 'flv',
                'title': 'The Man in Black: Series 3: The Printed Name',
                'description': "Mark Gatiss introduces Nicholas Pierpan's chilling tale of a writer's devilish pact with a mysterious man. Stars Ewan Bailey.",
                'duration': 1800,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'Episode is no longer available on BBC iPlayer Radio',
        },
        {
            'url': 'http://www.bbc.co.uk/iplayer/episode/b03vhd1f/The_Voice_UK_Series_3_Blind_Auditions_5/',
            'info_dict': {
                'id': 'b00yng1d',
                'ext': 'flv',
                'title': 'The Voice UK: Series 3: Blind Auditions 5',
                'description': 'Emma Willis and Marvin Humes present the fifth set of blind auditions in the singing competition, as the coaches continue to build their teams based on voice alone.',
                'duration': 5100,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'Currently BBC iPlayer TV programmes are available to play in the UK only',
        },
        {
            'url': 'http://www.bbc.co.uk/iplayer/episode/p026c7jt/tomorrows-worlds-the-unearthly-history-of-science-fiction-2-invasion',
            'info_dict': {
                'id': 'b03k3pb7',
                'ext': 'flv',
                'title': "Tomorrow's Worlds: The Unearthly History of Science Fiction",
                'description': '2. Invasion',
                'duration': 3600,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'Currently BBC iPlayer TV programmes are available to play in the UK only',
        }, {
            'url': 'http://www.bbc.co.uk/programmes/b04v20dw',
            'info_dict': {
                'id': 'b04v209v',
                'ext': 'flv',
                'title': 'Pete Tong, The Essential New Tune Special',
                'description': "Pete has a very special mix - all of 2014's Essential New Tunes!",
                'duration': 10800,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'Episode is no longer available on BBC iPlayer Radio',
        }, {
            'url': 'http://www.bbc.co.uk/music/clips/p022h44b',
            'note': 'Audio',
            'info_dict': {
                'id': 'p022h44j',
                'ext': 'flv',
                'title': 'BBC Proms Music Guides, Rachmaninov: Symphonic Dances',
                'description': "In this Proms Music Guide, Andrew McGregor looks at Rachmaninov's Symphonic Dances.",
                'duration': 227,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            }
        }, {
            'url': 'http://www.bbc.co.uk/music/clips/p025c0zz',
            'note': 'Video',
            'info_dict': {
                'id': 'p025c103',
                'ext': 'flv',
                'title': 'Reading and Leeds Festival, 2014, Rae Morris - Closer (Live on BBC Three)',
                'description': 'Rae Morris performs Closer for BBC Three at Reading 2014',
                'duration': 226,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            }
        }, {
            'url': 'http://www.bbc.co.uk/iplayer/episode/b054fn09/ad/natural-world-20152016-2-super-powered-owls',
            'info_dict': {
                'id': 'p02n76xf',
                'ext': 'flv',
                'title': 'Natural World, 2015-2016: 2. Super Powered Owls',
                'description': 'md5:e4db5c937d0e95a7c6b5e654d429183d',
                'duration': 3540,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'geolocation',
        }, {
            'url': 'http://www.bbc.co.uk/iplayer/episode/b05zmgwn/royal-academy-summer-exhibition',
            'info_dict': {
                'id': 'b05zmgw1',
                'ext': 'flv',
                'description': 'Kirsty Wark and Morgan Quaintance visit the Royal Academy as it prepares for its annual artistic extravaganza, meeting people who have come together to make the show unique.',
                'title': 'Royal Academy Summer Exhibition',
                'duration': 3540,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'geolocation',
        }, {
            # iptv-all mediaset fails with geolocation however there is no geo restriction
            # for this programme at all
            'url': 'http://www.bbc.co.uk/programmes/b06rkn85',
            'info_dict': {
                'id': 'b06rkms3',
                'ext': 'flv',
                'title': "Best of the Mini-Mixes 2015: Part 3, Annie Mac's Friday Night - BBC Radio 1",
                'description': "Annie has part three in the Best of the Mini-Mixes 2015, plus the year's Most Played!",
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'Now it\'s really geo-restricted',
        }, {
            # compact player (https://github.com/ytdl-org/youtube-dl/issues/8147)
            'url': 'http://www.bbc.co.uk/programmes/p028bfkf/player',
            'info_dict': {
                'id': 'p028bfkj',
                'ext': 'flv',
                'title': 'Extract from BBC documentary Look Stranger - Giant Leeks and Magic Brews',
                'description': 'Extract from BBC documentary Look Stranger - Giant Leeks and Magic Brews',
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        }, {
            'url': 'https://www.bbc.co.uk/sounds/play/m0007jzb',
            'note': 'Audio',
            'info_dict': {
                'id': 'm0007jz9',
                'ext': 'mp4',
                'title': 'BBC Proms, 2019, Prom 34: West–Eastern Divan Orchestra',
                'description': "Live BBC Proms. West–Eastern Divan Orchestra with Daniel Barenboim and Martha Argerich.",
                'duration': 9840,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            }
        }, {
            'url': 'http://www.bbc.co.uk/iplayer/playlist/p01dvks4',
            'only_matching': True,
        }, {
            'url': 'http://www.bbc.co.uk/music/clips#p02frcc3',
            'only_matching': True,
        }, {
            'url': 'http://www.bbc.co.uk/iplayer/cbeebies/episode/b0480276/bing-14-atchoo',
            'only_matching': True,
        }, {
            'url': 'http://www.bbc.co.uk/radio/player/p03cchwf',
            'only_matching': True,
        }, {
            'url': 'https://www.bbc.co.uk/music/audiovideo/popular#p055bc55',
            'only_matching': True,
        }, {
            'url': 'http://www.bbc.co.uk/programmes/w3csv1y9',
            'only_matching': True,
        }, {
            'url': 'https://www.bbc.co.uk/programmes/m00005xn',
            'only_matching': True,
        }, {
            'url': 'https://www.bbc.co.uk/programmes/w172w4dww1jqt5s',
            'only_matching': True,
        }]

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return

        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading signin page')

        login_form = self._hidden_inputs(login_page)

        login_form.update({
            'username': username,
            'password': password,
        })

        post_url = urljoin(self._LOGIN_URL, self._search_regex(
            r'<form[^>]+action=(["\'])(?P<url>.+?)\1', login_page,
            'post url', default=self._LOGIN_URL, group='url'))

        response, urlh = self._download_webpage_handle(
            post_url, None, 'Logging in', data=urlencode_postdata(login_form),
            headers={'Referer': self._LOGIN_URL})

        if self._LOGIN_URL in urlh.geturl():
            error = clean_html(get_element_by_class('form-message', response))
            if error:
                raise ExtractorError(
                    'Unable to login: %s' % error, expected=True)
            raise ExtractorError('Unable to log in')

    def _real_initialize(self):
        self._login()

    class MediaSelectionError(Exception):
        def __init__(self, id):
            self.id = id

    def _extract_asx_playlist(self, connection, programme_id):
        asx = self._download_xml(connection.get('href'), programme_id, 'Downloading ASX playlist')
        return [ref.get('href') for ref in asx.findall('./Entry/ref')]

    def _extract_items(self, playlist):
        return playlist.findall('./{%s}item' % self._EMP_PLAYLIST_NS)

    def _extract_medias(self, media_selection):
        error = media_selection.get('result')
        if error:
            raise BBCCoUkIE.MediaSelectionError(error)
        return media_selection.get('media') or []

    def _extract_connections(self, media):
        return media.get('connection') or []

    def _get_subtitles(self, media, programme_id):
        subtitles = {}
        for connection in self._extract_connections(media):
            cc_url = url_or_none(connection.get('href'))
            if not cc_url:
                continue
            captions = self._download_xml(
                cc_url, programme_id, 'Downloading captions', fatal=False)
            if not isinstance(captions, compat_etree_Element):
                continue
            subtitles['en'] = [
                {
                    'url': connection.get('href'),
                    'ext': 'ttml',
                },
            ]
            break
        return subtitles

    def _raise_extractor_error(self, media_selection_error):
        raise ExtractorError(
            '%s returned error: %s' % (self.IE_NAME, media_selection_error.id),
            expected=True)

    def _download_media_selector(self, programme_id):
        last_exception = None
        for media_set in self._MEDIA_SETS:
            try:
                return self._download_media_selector_url(
                    self._MEDIA_SELECTOR_URL_TEMPL % (media_set, programme_id), programme_id)
            except BBCCoUkIE.MediaSelectionError as e:
                if e.id in ('notukerror', 'geolocation', 'selectionunavailable'):
                    last_exception = e
                    continue
                self._raise_extractor_error(e)
        self._raise_extractor_error(last_exception)

    def _download_media_selector_url(self, url, programme_id=None):
        media_selection = self._download_json(
            url, programme_id, 'Downloading media selection JSON',
            expected_status=(403, 404))
        return self._process_media_selector(media_selection, programme_id)

    def _process_media_selector(self, media_selection, programme_id):
        formats = []
        subtitles = None
        urls = []

        for media in self._extract_medias(media_selection):
            kind = media.get('kind')
            if kind in ('video', 'audio'):
                bitrate = int_or_none(media.get('bitrate'))
                encoding = media.get('encoding')
                width = int_or_none(media.get('width'))
                height = int_or_none(media.get('height'))
                file_size = int_or_none(media.get('media_file_size'))
                for connection in self._extract_connections(media):
                    href = connection.get('href')
                    if href in urls:
                        continue
                    if href:
                        urls.append(href)
                    conn_kind = connection.get('kind')
                    protocol = connection.get('protocol')
                    supplier = connection.get('supplier')
                    transfer_format = connection.get('transferFormat')
                    format_id = supplier or conn_kind or protocol
                    # ASX playlist
                    if supplier == 'asx':
                        for i, ref in enumerate(self._extract_asx_playlist(connection, programme_id)):
                            formats.append({
                                'url': ref,
                                'format_id': 'ref%s_%s' % (i, format_id),
                            })
                    elif transfer_format == 'dash':
                        formats.extend(self._extract_mpd_formats(
                            href, programme_id, mpd_id=format_id, fatal=False))
                    elif transfer_format == 'hls':
                        formats.extend(self._extract_m3u8_formats(
                            href, programme_id, ext='mp4', entry_protocol='m3u8_native',
                            m3u8_id=format_id, fatal=False))
                    elif transfer_format == 'hds':
                        formats.extend(self._extract_f4m_formats(
                            href, programme_id, f4m_id=format_id, fatal=False))
                    else:
                        if not supplier and bitrate:
                            format_id += '-%d' % bitrate
                        fmt = {
                            'format_id': format_id,
                            'filesize': file_size,
                        }
                        if kind == 'video':
                            fmt.update({
                                'width': width,
                                'height': height,
                                'tbr': bitrate,
                                'vcodec': encoding,
                            })
                        else:
                            fmt.update({
                                'abr': bitrate,
                                'acodec': encoding,
                                'vcodec': 'none',
                            })
                        if protocol in ('http', 'https'):
                            # Direct link
                            fmt.update({
                                'url': href,
                            })
                        elif protocol == 'rtmp':
                            application = connection.get('application', 'ondemand')
                            auth_string = connection.get('authString')
                            identifier = connection.get('identifier')
                            server = connection.get('server')
                            fmt.update({
                                'url': '%s://%s/%s?%s' % (protocol, server, application, auth_string),
                                'play_path': identifier,
                                'app': '%s?%s' % (application, auth_string),
                                'page_url': 'http://www.bbc.co.uk',
                                'player_url': 'http://www.bbc.co.uk/emp/releases/iplayer/revisions/617463_618125_4/617463_618125_4_emp.swf',
                                'rtmp_live': False,
                                'ext': 'flv',
                            })
                        else:
                            continue
                        formats.append(fmt)
            elif kind == 'captions':
                subtitles = self.extract_subtitles(media, programme_id)
        return formats, subtitles

    def _download_playlist(self, playlist_id):
        try:
            playlist = self._download_json(
                'http://www.bbc.co.uk/programmes/%s/playlist.json' % playlist_id,
                playlist_id, 'Downloading playlist JSON')

            version = playlist.get('defaultAvailableVersion')
            if version:
                smp_config = version['smpConfig']
                title = smp_config['title']
                description = smp_config['summary']
                for item in smp_config['items']:
                    kind = item['kind']
                    if kind not in ('programme', 'radioProgramme'):
                        continue
                    programme_id = item.get('vpid')
                    duration = int_or_none(item.get('duration'))
                    formats, subtitles = self._download_media_selector(programme_id)
                return programme_id, title, description, duration, formats, subtitles
        except ExtractorError as ee:
            if not (isinstance(ee.cause, compat_HTTPError) and ee.cause.code == 404):
                raise

        # fallback to legacy playlist
        return self._process_legacy_playlist(playlist_id)

    def _process_legacy_playlist_url(self, url, display_id):
        playlist = self._download_legacy_playlist_url(url, display_id)
        return self._extract_from_legacy_playlist(playlist, display_id)

    def _process_legacy_playlist(self, playlist_id):
        return self._process_legacy_playlist_url(
            'http://www.bbc.co.uk/iplayer/playlist/%s' % playlist_id, playlist_id)

    def _download_legacy_playlist_url(self, url, playlist_id=None):
        return self._download_xml(
            url, playlist_id, 'Downloading legacy playlist XML')

    def _extract_from_legacy_playlist(self, playlist, playlist_id):
        no_items = playlist.find('./{%s}noItems' % self._EMP_PLAYLIST_NS)
        if no_items is not None:
            reason = no_items.get('reason')
            if reason == 'preAvailability':
                msg = 'Episode %s is not yet available' % playlist_id
            elif reason == 'postAvailability':
                msg = 'Episode %s is no longer available' % playlist_id
            elif reason == 'noMedia':
                msg = 'Episode %s is not currently available' % playlist_id
            else:
                msg = 'Episode %s is not available: %s' % (playlist_id, reason)
            raise ExtractorError(msg, expected=True)

        for item in self._extract_items(playlist):
            kind = item.get('kind')
            if kind not in ('programme', 'radioProgramme'):
                continue
            title = playlist.find('./{%s}title' % self._EMP_PLAYLIST_NS).text
            description_el = playlist.find('./{%s}summary' % self._EMP_PLAYLIST_NS)
            description = description_el.text if description_el is not None else None

            def get_programme_id(item):
                def get_from_attributes(item):
                    for p in ('identifier', 'group'):
                        value = item.get(p)
                        if value and re.match(r'^[pb][\da-z]{7}$', value):
                            return value
                get_from_attributes(item)
                mediator = item.find('./{%s}mediator' % self._EMP_PLAYLIST_NS)
                if mediator is not None:
                    return get_from_attributes(mediator)

            programme_id = get_programme_id(item)
            duration = int_or_none(item.get('duration'))

            if programme_id:
                formats, subtitles = self._download_media_selector(programme_id)
            else:
                formats, subtitles = self._process_media_selector(item, playlist_id)
                programme_id = playlist_id

        return programme_id, title, description, duration, formats, subtitles

    def _real_extract(self, url):
        group_id = self._match_id(url)

        webpage = self._download_webpage(url, group_id, 'Downloading video page')

        error = self._search_regex(
            r'<div\b[^>]+\bclass=["\'](?:smp|playout)__message delta["\'][^>]*>\s*([^<]+?)\s*<',
            webpage, 'error', default=None)
        if error:
            raise ExtractorError(error, expected=True)

        programme_id = None
        duration = None

        tviplayer = self._search_regex(
            r'mediator\.bind\(({.+?})\s*,\s*document\.getElementById',
            webpage, 'player', default=None)

        if tviplayer:
            player = self._parse_json(tviplayer, group_id).get('player', {})
            duration = int_or_none(player.get('duration'))
            programme_id = player.get('vpid')

        if not programme_id:
            programme_id = self._search_regex(
                r'"vpid"\s*:\s*"(%s)"' % self._ID_REGEX, webpage, 'vpid', fatal=False, default=None)

        if programme_id:
            formats, subtitles = self._download_media_selector(programme_id)
            title = self._og_search_title(webpage, default=None) or self._html_search_regex(
                (r'<h2[^>]+id="parent-title"[^>]*>(.+?)</h2>',
                 r'<div[^>]+class="info"[^>]*>\s*<h1>(.+?)</h1>'), webpage, 'title')
            description = self._search_regex(
                (r'<p class="[^"]*medium-description[^"]*">([^<]+)</p>',
                 r'<div[^>]+class="info_+synopsis"[^>]*>([^<]+)</div>'),
                webpage, 'description', default=None)
            if not description:
                description = self._html_search_meta('description', webpage)
        else:
            programme_id, title, description, duration, formats, subtitles = self._download_playlist(group_id)

        self._sort_formats(formats)

        return {
            'id': programme_id,
            'title': title,
            'description': description,
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
        }


class BBCIE(BBCCoUkIE):
    IE_NAME = 'bbc'
    IE_DESC = 'BBC'
    _VALID_URL = r'https?://(?:www\.)?bbc\.(?:com|co\.uk)/(?:[^/]+/)+(?P<id>[^/#?]+)'

    _MEDIA_SETS = [
        'mobile-tablet-main',
        'pc',
    ]

    _TESTS = [{
        # article with multiple videos embedded with data-playable containing vpids
        'url': 'http://www.bbc.com/news/world-europe-32668511',
        'info_dict': {
            'id': 'world-europe-32668511',
            'title': 'Russia stages massive WW2 parade',
            'description': 'md5:00ff61976f6081841f759a08bf78cc9c',
        },
        'playlist_count': 2,
    }, {
        # article with multiple videos embedded with data-playable (more videos)
        'url': 'http://www.bbc.com/news/business-28299555',
        'info_dict': {
            'id': 'business-28299555',
            'title': 'Farnborough Airshow: Video highlights',
            'description': 'BBC reports and video highlights at the Farnborough Airshow.',
        },
        'playlist_count': 9,
        'skip': 'Save time',
    }, {
        # article with multiple videos embedded with `new SMP()`
        # broken
        'url': 'http://www.bbc.co.uk/blogs/adamcurtis/entries/3662a707-0af9-3149-963f-47bea720b460',
        'info_dict': {
            'id': '3662a707-0af9-3149-963f-47bea720b460',
            'title': 'BUGGER',
        },
        'playlist_count': 18,
    }, {
        # single video embedded with data-playable containing vpid
        'url': 'http://www.bbc.com/news/world-europe-32041533',
        'info_dict': {
            'id': 'p02mprgb',
            'ext': 'mp4',
            'title': 'Aerial footage showed the site of the crash in the Alps - courtesy BFM TV',
            'description': 'md5:2868290467291b37feda7863f7a83f54',
            'duration': 47,
            'timestamp': 1427219242,
            'upload_date': '20150324',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        }
    }, {
        # article with single video embedded with data-playable containing XML playlist
        # with direct video links as progressiveDownloadUrl (for now these are extracted)
        # and playlist with f4m and m3u8 as streamingUrl
        'url': 'http://www.bbc.com/turkce/haberler/2015/06/150615_telabyad_kentin_cogu',
        'info_dict': {
            'id': '150615_telabyad_kentin_cogu',
            'ext': 'mp4',
            'title': "YPG: Tel Abyad'ın tamamı kontrolümüzde",
            'description': 'md5:33a4805a855c9baf7115fcbde57e7025',
            'timestamp': 1434397334,
            'upload_date': '20150615',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # single video embedded with data-playable containing XML playlists (regional section)
        'url': 'http://www.bbc.com/mundo/video_fotos/2015/06/150619_video_honduras_militares_hospitales_corrupcion_aw',
        'info_dict': {
            'id': '150619_video_honduras_militares_hospitales_corrupcion_aw',
            'ext': 'mp4',
            'title': 'Honduras militariza sus hospitales por nuevo escándalo de corrupción',
            'description': 'md5:1525f17448c4ee262b64b8f0c9ce66c8',
            'timestamp': 1434713142,
            'upload_date': '20150619',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # single video from video playlist embedded with vxp-playlist-data JSON
        'url': 'http://www.bbc.com/news/video_and_audio/must_see/33376376',
        'info_dict': {
            'id': 'p02w6qjc',
            'ext': 'mp4',
            'title': '''Judge Mindy Glazer: "I'm sorry to see you here... I always wondered what happened to you"''',
            'duration': 56,
            'description': '''Judge Mindy Glazer: "I'm sorry to see you here... I always wondered what happened to you"''',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # single video story with digitalData
        'url': 'http://www.bbc.com/travel/story/20150625-sri-lankas-spicy-secret',
        'info_dict': {
            'id': 'p02q6gc4',
            'ext': 'flv',
            'title': 'Sri Lanka’s spicy secret',
            'description': 'As a new train line to Jaffna opens up the country’s north, travellers can experience a truly distinct slice of Tamil culture.',
            'timestamp': 1437674293,
            'upload_date': '20150723',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        }
    }, {
        # single video story without digitalData
        'url': 'http://www.bbc.com/autos/story/20130513-hyundais-rock-star',
        'info_dict': {
            'id': 'p018zqqg',
            'ext': 'mp4',
            'title': 'Hyundai Santa Fe Sport: Rock star',
            'description': 'md5:b042a26142c4154a6e472933cf20793d',
            'timestamp': 1415867444,
            'upload_date': '20141113',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        }
    }, {
        # single video embedded with Morph
        'url': 'http://www.bbc.co.uk/sport/live/olympics/36895975',
        'info_dict': {
            'id': 'p041vhd0',
            'ext': 'mp4',
            'title': "Nigeria v Japan - Men's First Round",
            'description': 'Live coverage of the first round from Group B at the Amazonia Arena.',
            'duration': 7980,
            'uploader': 'BBC Sport',
            'uploader_id': 'bbc_sport',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'Georestricted to UK',
    }, {
        # single video with playlist.sxml URL in playlist param
        'url': 'http://www.bbc.com/sport/0/football/33653409',
        'info_dict': {
            'id': 'p02xycnp',
            'ext': 'mp4',
            'title': 'Transfers: Cristiano Ronaldo to Man Utd, Arsenal to spend?',
            'description': 'BBC Sport\'s David Ornstein has the latest transfer gossip, including rumours of a Manchester United return for Cristiano Ronaldo.',
            'duration': 140,
        },
        'params': {
            # rtmp download
            'skip_download': True,
        }
    }, {
        # article with multiple videos embedded with playlist.sxml in playlist param
        'url': 'http://www.bbc.com/sport/0/football/34475836',
        'info_dict': {
            'id': '34475836',
            'title': 'Jurgen Klopp: Furious football from a witty and winning coach',
            'description': 'Fast-paced football, wit, wisdom and a ready smile - why Liverpool fans should come to love new boss Jurgen Klopp.',
        },
        'playlist_count': 3,
    }, {
        # school report article with single video
        'url': 'http://www.bbc.co.uk/schoolreport/35744779',
        'info_dict': {
            'id': '35744779',
            'title': 'School which breaks down barriers in Jerusalem',
        },
        'playlist_count': 1,
    }, {
        # single video with playlist URL from weather section
        'url': 'http://www.bbc.com/weather/features/33601775',
        'only_matching': True,
    }, {
        # custom redirection to www.bbc.com
        'url': 'http://www.bbc.co.uk/news/science-environment-33661876',
        'only_matching': True,
    }, {
        # single video article embedded with data-media-vpid
        'url': 'http://www.bbc.co.uk/sport/rowing/35908187',
        'only_matching': True,
    }, {
        'url': 'https://www.bbc.co.uk/bbcthree/clip/73d0bbd0-abc3-4cea-b3c0-cdae21905eb1',
        'info_dict': {
            'id': 'p06556y7',
            'ext': 'mp4',
            'title': 'Transfers: Cristiano Ronaldo to Man Utd, Arsenal to spend?',
            'description': 'md5:4b7dfd063d5a789a1512e99662be3ddd',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # window.__PRELOADED_STATE__
        'url': 'https://www.bbc.co.uk/radio/play/b0b9z4yl',
        'info_dict': {
            'id': 'b0b9z4vz',
            'ext': 'mp4',
            'title': 'Prom 6: An American in Paris and Turangalila',
            'description': 'md5:51cf7d6f5c8553f197e58203bc78dff8',
            'uploader': 'Radio 3',
            'uploader_id': 'bbc_radio_three',
        },
    }, {
        'url': 'http://www.bbc.co.uk/learningenglish/chinese/features/lingohack/ep-181227',
        'info_dict': {
            'id': 'p06w9tws',
            'ext': 'mp4',
            'title': 'md5:2fabf12a726603193a2879a055f72514',
            'description': 'Learn English words and phrases from this story',
        },
        'add_ie': [BBCCoUkIE.ie_key()],
    }, {
        # BBC Reel
        'url': 'https://www.bbc.com/reel/video/p07c6sb6/how-positive-thinking-is-harming-your-happiness',
        'info_dict': {
            'id': 'p07c6sb9',
            'ext': 'mp4',
            'title': 'How positive thinking is harming your happiness',
            'alt_title': 'The downsides of positive thinking',
            'description': 'md5:fad74b31da60d83b8265954ee42d85b4',
            'duration': 235,
            'thumbnail': r're:https?://.+/p07c9dsr.jpg',
            'upload_date': '20190604',
            'categories': ['Psychology'],
        },
    }]

    @classmethod
    def suitable(cls, url):
        EXCLUDE_IE = (BBCCoUkIE, BBCCoUkArticleIE, BBCCoUkIPlayerEpisodesIE, BBCCoUkIPlayerGroupIE, BBCCoUkPlaylistIE)
        return (False if any(ie.suitable(url) for ie in EXCLUDE_IE)
                else super(BBCIE, cls).suitable(url))

    def _extract_from_media_meta(self, media_meta, video_id):
        # Direct links to media in media metadata (e.g.
        # http://www.bbc.com/turkce/haberler/2015/06/150615_telabyad_kentin_cogu)
        # TODO: there are also f4m and m3u8 streams incorporated in playlist.sxml
        source_files = media_meta.get('sourceFiles')
        if source_files:
            return [{
                'url': f['url'],
                'format_id': format_id,
                'ext': f.get('encoding'),
                'tbr': float_or_none(f.get('bitrate'), 1000),
                'filesize': int_or_none(f.get('filesize')),
            } for format_id, f in source_files.items() if f.get('url')], []

        programme_id = media_meta.get('externalId')
        if programme_id:
            return self._download_media_selector(programme_id)

        # Process playlist.sxml as legacy playlist
        href = media_meta.get('href')
        if href:
            playlist = self._download_legacy_playlist_url(href)
            _, _, _, _, formats, subtitles = self._extract_from_legacy_playlist(playlist, video_id)
            return formats, subtitles

        return [], []

    def _extract_from_playlist_sxml(self, url, playlist_id, timestamp):
        programme_id, title, description, duration, formats, subtitles = \
            self._process_legacy_playlist_url(url, playlist_id)
        self._sort_formats(formats)
        return {
            'id': programme_id,
            'title': title,
            'description': description,
            'duration': duration,
            'timestamp': timestamp,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        json_ld_info = self._search_json_ld(webpage, playlist_id, default={})
        timestamp = json_ld_info.get('timestamp')

        playlist_title = json_ld_info.get('title')
        if not playlist_title:
            playlist_title = self._og_search_title(
                webpage, default=None) or self._html_search_regex(
                r'<title>(.+?)</title>', webpage, 'playlist title', default=None)
            if playlist_title:
                playlist_title = re.sub(r'(.+)\s*-\s*BBC.*?$', r'\1', playlist_title).strip()

        playlist_description = json_ld_info.get(
            'description') or self._og_search_description(webpage, default=None)

        if not timestamp:
            timestamp = parse_iso8601(self._search_regex(
                [r'<meta[^>]+property="article:published_time"[^>]+content="([^"]+)"',
                 r'itemprop="datePublished"[^>]+datetime="([^"]+)"',
                 r'"datePublished":\s*"([^"]+)'],
                webpage, 'date', default=None))

        entries = []

        # article with multiple videos embedded with playlist.sxml (e.g.
        # http://www.bbc.com/sport/0/football/34475836)
        playlists = re.findall(r'<param[^>]+name="playlist"[^>]+value="([^"]+)"', webpage)
        playlists.extend(re.findall(r'data-media-id="([^"]+/playlist\.sxml)"', webpage))
        if playlists:
            entries = [
                self._extract_from_playlist_sxml(playlist_url, playlist_id, timestamp)
                for playlist_url in playlists]

        # news article with multiple videos embedded with data-playable
        data_playables = re.findall(r'data-playable=(["\'])({.+?})\1', webpage)
        if data_playables:
            for _, data_playable_json in data_playables:
                data_playable = self._parse_json(
                    unescapeHTML(data_playable_json), playlist_id, fatal=False)
                if not data_playable:
                    continue
                settings = data_playable.get('settings', {})
                if settings:
                    # data-playable with video vpid in settings.playlistObject.items (e.g.
                    # http://www.bbc.com/news/world-us-canada-34473351)
                    playlist_object = settings.get('playlistObject', {})
                    if playlist_object:
                        items = playlist_object.get('items')
                        if items and isinstance(items, list):
                            title = playlist_object['title']
                            description = playlist_object.get('summary')
                            duration = int_or_none(items[0].get('duration'))
                            programme_id = items[0].get('vpid')
                            formats, subtitles = self._download_media_selector(programme_id)
                            self._sort_formats(formats)
                            entries.append({
                                'id': programme_id,
                                'title': title,
                                'description': description,
                                'timestamp': timestamp,
                                'duration': duration,
                                'formats': formats,
                                'subtitles': subtitles,
                            })
                    else:
                        # data-playable without vpid but with a playlist.sxml URLs
                        # in otherSettings.playlist (e.g.
                        # http://www.bbc.com/turkce/multimedya/2015/10/151010_vid_ankara_patlama_ani)
                        playlist = data_playable.get('otherSettings', {}).get('playlist', {})
                        if playlist:
                            entry = None
                            for key in ('streaming', 'progressiveDownload'):
                                playlist_url = playlist.get('%sUrl' % key)
                                if not playlist_url:
                                    continue
                                try:
                                    info = self._extract_from_playlist_sxml(
                                        playlist_url, playlist_id, timestamp)
                                    if not entry:
                                        entry = info
                                    else:
                                        entry['title'] = info['title']
                                        entry['formats'].extend(info['formats'])
                                except ExtractorError as e:
                                    # Some playlist URL may fail with 500, at the same time
                                    # the other one may work fine (e.g.
                                    # http://www.bbc.com/turkce/haberler/2015/06/150615_telabyad_kentin_cogu)
                                    if isinstance(e.cause, compat_HTTPError) and e.cause.code == 500:
                                        continue
                                    raise
                            if entry:
                                self._sort_formats(entry['formats'])
                                entries.append(entry)

        if entries:
            return self.playlist_result(entries, playlist_id, playlist_title, playlist_description)

        # http://www.bbc.co.uk/learningenglish/chinese/features/lingohack/ep-181227
        group_id = self._search_regex(
            r'<div[^>]+\bclass=["\']video["\'][^>]+\bdata-pid=["\'](%s)' % self._ID_REGEX,
            webpage, 'group id', default=None)
        if group_id:
            return self.url_result(
                'https://www.bbc.co.uk/programmes/%s' % group_id,
                ie=BBCCoUkIE.ie_key())

        # single video story (e.g. http://www.bbc.com/travel/story/20150625-sri-lankas-spicy-secret)
        programme_id = self._search_regex(
            [r'data-(?:video-player|media)-vpid="(%s)"' % self._ID_REGEX,
             r'<param[^>]+name="externalIdentifier"[^>]+value="(%s)"' % self._ID_REGEX,
             r'videoId\s*:\s*["\'](%s)["\']' % self._ID_REGEX],
            webpage, 'vpid', default=None)

        if programme_id:
            formats, subtitles = self._download_media_selector(programme_id)
            self._sort_formats(formats)
            # digitalData may be missing (e.g. http://www.bbc.com/autos/story/20130513-hyundais-rock-star)
            digital_data = self._parse_json(
                self._search_regex(
                    r'var\s+digitalData\s*=\s*({.+?});?\n', webpage, 'digital data', default='{}'),
                programme_id, fatal=False)
            page_info = digital_data.get('page', {}).get('pageInfo', {})
            title = page_info.get('pageName') or self._og_search_title(webpage)
            description = page_info.get('description') or self._og_search_description(webpage)
            timestamp = parse_iso8601(page_info.get('publicationDate')) or timestamp
            return {
                'id': programme_id,
                'title': title,
                'description': description,
                'timestamp': timestamp,
                'formats': formats,
                'subtitles': subtitles,
            }

        # bbc reel (e.g. https://www.bbc.com/reel/video/p07c6sb6/how-positive-thinking-is-harming-your-happiness)
        initial_data = self._parse_json(self._html_search_regex(
            r'<script[^>]+id=(["\'])initial-data\1[^>]+data-json=(["\'])(?P<json>(?:(?!\2).)+)',
            webpage, 'initial data', default='{}', group='json'), playlist_id, fatal=False)
        if initial_data:
            init_data = try_get(
                initial_data, lambda x: x['initData']['items'][0], dict) or {}
            smp_data = init_data.get('smpData') or {}
            clip_data = try_get(smp_data, lambda x: x['items'][0], dict) or {}
            version_id = clip_data.get('versionID')
            if version_id:
                title = smp_data['title']
                formats, subtitles = self._download_media_selector(version_id)
                self._sort_formats(formats)
                image_url = smp_data.get('holdingImageURL')
                display_date = init_data.get('displayDate')
                topic_title = init_data.get('topicTitle')

                return {
                    'id': version_id,
                    'title': title,
                    'formats': formats,
                    'alt_title': init_data.get('shortTitle'),
                    'thumbnail': image_url.replace('$recipe', 'raw') if image_url else None,
                    'description': smp_data.get('summary') or init_data.get('shortSummary'),
                    'upload_date': display_date.replace('-', '') if display_date else None,
                    'subtitles': subtitles,
                    'duration': int_or_none(clip_data.get('duration')),
                    'categories': [topic_title] if topic_title else None,
                }

        # Morph based embed (e.g. http://www.bbc.co.uk/sport/live/olympics/36895975)
        # There are several setPayload calls may be present but the video
        # seems to be always related to the first one
        morph_payload = self._parse_json(
            self._search_regex(
                r'Morph\.setPayload\([^,]+,\s*({.+?})\);',
                webpage, 'morph payload', default='{}'),
            playlist_id, fatal=False)
        if morph_payload:
            components = try_get(morph_payload, lambda x: x['body']['components'], list) or []
            for component in components:
                if not isinstance(component, dict):
                    continue
                lead_media = try_get(component, lambda x: x['props']['leadMedia'], dict)
                if not lead_media:
                    continue
                identifiers = lead_media.get('identifiers')
                if not identifiers or not isinstance(identifiers, dict):
                    continue
                programme_id = identifiers.get('vpid') or identifiers.get('playablePid')
                if not programme_id:
                    continue
                title = lead_media.get('title') or self._og_search_title(webpage)
                formats, subtitles = self._download_media_selector(programme_id)
                self._sort_formats(formats)
                description = lead_media.get('summary')
                uploader = lead_media.get('masterBrand')
                uploader_id = lead_media.get('mid')
                duration = None
                duration_d = lead_media.get('duration')
                if isinstance(duration_d, dict):
                    duration = parse_duration(dict_get(
                        duration_d, ('rawDuration', 'formattedDuration', 'spokenDuration')))
                return {
                    'id': programme_id,
                    'title': title,
                    'description': description,
                    'duration': duration,
                    'uploader': uploader,
                    'uploader_id': uploader_id,
                    'formats': formats,
                    'subtitles': subtitles,
                }

        preload_state = self._parse_json(self._search_regex(
            r'window\.__PRELOADED_STATE__\s*=\s*({.+?});', webpage,
            'preload state', default='{}'), playlist_id, fatal=False)
        if preload_state:
            current_programme = preload_state.get('programmes', {}).get('current') or {}
            programme_id = current_programme.get('id')
            if current_programme and programme_id and current_programme.get('type') == 'playable_item':
                title = current_programme.get('titles', {}).get('tertiary') or playlist_title
                formats, subtitles = self._download_media_selector(programme_id)
                self._sort_formats(formats)
                synopses = current_programme.get('synopses') or {}
                network = current_programme.get('network') or {}
                duration = int_or_none(
                    current_programme.get('duration', {}).get('value'))
                thumbnail = None
                image_url = current_programme.get('image_url')
                if image_url:
                    thumbnail = image_url.replace('{recipe}', 'raw')
                return {
                    'id': programme_id,
                    'title': title,
                    'description': dict_get(synopses, ('long', 'medium', 'short')),
                    'thumbnail': thumbnail,
                    'duration': duration,
                    'uploader': network.get('short_title'),
                    'uploader_id': network.get('id'),
                    'formats': formats,
                    'subtitles': subtitles,
                }

        bbc3_config = self._parse_json(
            self._search_regex(
                r'(?s)bbcthreeConfig\s*=\s*({.+?})\s*;\s*<', webpage,
                'bbcthree config', default='{}'),
            playlist_id, transform_source=js_to_json, fatal=False) or {}
        payload = bbc3_config.get('payload') or {}
        if payload:
            clip = payload.get('currentClip') or {}
            clip_vpid = clip.get('vpid')
            clip_title = clip.get('title')
            if clip_vpid and clip_title:
                formats, subtitles = self._download_media_selector(clip_vpid)
                self._sort_formats(formats)
                return {
                    'id': clip_vpid,
                    'title': clip_title,
                    'thumbnail': dict_get(clip, ('poster', 'imageUrl')),
                    'description': clip.get('description'),
                    'duration': parse_duration(clip.get('duration')),
                    'formats': formats,
                    'subtitles': subtitles,
                }
            bbc3_playlist = try_get(
                payload, lambda x: x['content']['bbcMedia']['playlist'],
                dict)
            if bbc3_playlist:
                playlist_title = bbc3_playlist.get('title') or playlist_title
                thumbnail = bbc3_playlist.get('holdingImageURL')
                entries = []
                for bbc3_item in bbc3_playlist['items']:
                    programme_id = bbc3_item.get('versionID')
                    if not programme_id:
                        continue
                    formats, subtitles = self._download_media_selector(programme_id)
                    self._sort_formats(formats)
                    entries.append({
                        'id': programme_id,
                        'title': playlist_title,
                        'thumbnail': thumbnail,
                        'timestamp': timestamp,
                        'formats': formats,
                        'subtitles': subtitles,
                    })
                return self.playlist_result(
                    entries, playlist_id, playlist_title, playlist_description)

        initial_data = self._parse_json(self._search_regex(
            r'window\.__INITIAL_DATA__\s*=\s*({.+?});', webpage,
            'preload state', default='{}'), playlist_id, fatal=False)
        if initial_data:
            def parse_media(media):
                if not media:
                    return
                for item in (try_get(media, lambda x: x['media']['items'], list) or []):
                    item_id = item.get('id')
                    item_title = item.get('title')
                    if not (item_id and item_title):
                        continue
                    formats, subtitles = self._download_media_selector(item_id)
                    self._sort_formats(formats)
                    entries.append({
                        'id': item_id,
                        'title': item_title,
                        'thumbnail': item.get('holdingImageUrl'),
                        'formats': formats,
                        'subtitles': subtitles,
                    })
            for resp in (initial_data.get('data') or {}).values():
                name = resp.get('name')
                if name == 'media-experience':
                    parse_media(try_get(resp, lambda x: x['data']['initialItem']['mediaItem'], dict))
                elif name == 'article':
                    for block in (try_get(resp, lambda x: x['data']['blocks'], list) or []):
                        if block.get('type') != 'media':
                            continue
                        parse_media(block.get('model'))
            return self.playlist_result(
                entries, playlist_id, playlist_title, playlist_description)

        def extract_all(pattern):
            return list(filter(None, map(
                lambda s: self._parse_json(s, playlist_id, fatal=False),
                re.findall(pattern, webpage))))

        # Multiple video article (e.g.
        # http://www.bbc.co.uk/blogs/adamcurtis/entries/3662a707-0af9-3149-963f-47bea720b460)
        EMBED_URL = r'https?://(?:www\.)?bbc\.co\.uk/(?:[^/]+/)+%s(?:\b[^"]+)?' % self._ID_REGEX
        entries = []
        for match in extract_all(r'new\s+SMP\(({.+?})\)'):
            embed_url = match.get('playerSettings', {}).get('externalEmbedUrl')
            if embed_url and re.match(EMBED_URL, embed_url):
                entries.append(embed_url)
        entries.extend(re.findall(
            r'setPlaylist\("(%s)"\)' % EMBED_URL, webpage))
        if entries:
            return self.playlist_result(
                [self.url_result(entry_, 'BBCCoUk') for entry_ in entries],
                playlist_id, playlist_title, playlist_description)

        # Multiple video article (e.g. http://www.bbc.com/news/world-europe-32668511)
        medias = extract_all(r"data-media-meta='({[^']+})'")

        if not medias:
            # Single video article (e.g. http://www.bbc.com/news/video_and_audio/international)
            media_asset = self._search_regex(
                r'mediaAssetPage\.init\(\s*({.+?}), "/',
                webpage, 'media asset', default=None)
            if media_asset:
                media_asset_page = self._parse_json(media_asset, playlist_id, fatal=False)
                medias = []
                for video in media_asset_page.get('videos', {}).values():
                    medias.extend(video.values())

        if not medias:
            # Multiple video playlist with single `now playing` entry (e.g.
            # http://www.bbc.com/news/video_and_audio/must_see/33767813)
            vxp_playlist = self._parse_json(
                self._search_regex(
                    r'<script[^>]+class="vxp-playlist-data"[^>]+type="application/json"[^>]*>([^<]+)</script>',
                    webpage, 'playlist data'),
                playlist_id)
            playlist_medias = []
            for item in vxp_playlist:
                media = item.get('media')
                if not media:
                    continue
                playlist_medias.append(media)
                # Download single video if found media with asset id matching the video id from URL
                if item.get('advert', {}).get('assetId') == playlist_id:
                    medias = [media]
                    break
            # Fallback to the whole playlist
            if not medias:
                medias = playlist_medias

        entries = []
        for num, media_meta in enumerate(medias, start=1):
            formats, subtitles = self._extract_from_media_meta(media_meta, playlist_id)
            if not formats:
                continue
            self._sort_formats(formats)

            video_id = media_meta.get('externalId')
            if not video_id:
                video_id = playlist_id if len(medias) == 1 else '%s-%s' % (playlist_id, num)

            title = media_meta.get('caption')
            if not title:
                title = playlist_title if len(medias) == 1 else '%s - Video %s' % (playlist_title, num)

            duration = int_or_none(media_meta.get('durationInSeconds')) or parse_duration(media_meta.get('duration'))

            images = []
            for image in media_meta.get('images', {}).values():
                images.extend(image.values())
            if 'image' in media_meta:
                images.append(media_meta['image'])

            thumbnails = [{
                'url': image.get('href'),
                'width': int_or_none(image.get('width')),
                'height': int_or_none(image.get('height')),
            } for image in images]

            entries.append({
                'id': video_id,
                'title': title,
                'thumbnails': thumbnails,
                'duration': duration,
                'timestamp': timestamp,
                'formats': formats,
                'subtitles': subtitles,
            })

        return self.playlist_result(entries, playlist_id, playlist_title, playlist_description)


class BBCCoUkArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bbc\.co\.uk/programmes/articles/(?P<id>[a-zA-Z0-9]+)'
    IE_NAME = 'bbc.co.uk:article'
    IE_DESC = 'BBC articles'

    _TEST = {
        'url': 'http://www.bbc.co.uk/programmes/articles/3jNQLTMrPlYGTBn0WV6M2MS/not-your-typical-role-model-ada-lovelace-the-19th-century-programmer',
        'info_dict': {
            'id': '3jNQLTMrPlYGTBn0WV6M2MS',
            'title': 'Calculating Ada: The Countess of Computing - Not your typical role model: Ada Lovelace the 19th century programmer - BBC Four',
            'description': 'Hannah Fry reveals some of her surprising discoveries about Ada Lovelace during filming.',
        },
        'playlist_count': 4,
        'add_ie': ['BBCCoUk'],
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        title = self._og_search_title(webpage)
        description = self._og_search_description(webpage).strip()

        entries = [self.url_result(programme_url) for programme_url in re.findall(
            r'<div[^>]+typeof="Clip"[^>]+resource="([^"]+)"', webpage)]

        return self.playlist_result(entries, playlist_id, title, description)


class BBCCoUkPlaylistBaseIE(InfoExtractor):
    def _entries(self, webpage, url, playlist_id):
        single_page = 'page' in compat_urlparse.parse_qs(
            compat_urlparse.urlparse(url).query)
        for page_num in itertools.count(2):
            for video_id in re.findall(
                    self._VIDEO_ID_TEMPLATE % BBCCoUkIE._ID_REGEX, webpage):
                yield self.url_result(
                    self._URL_TEMPLATE % video_id, BBCCoUkIE.ie_key())
            if single_page:
                return
            next_page = self._search_regex(
                r'<li[^>]+class=(["\'])pagination_+next\1[^>]*><a[^>]+href=(["\'])(?P<url>(?:(?!\2).)+)\2',
                webpage, 'next page url', default=None, group='url')
            if not next_page:
                break
            webpage = self._download_webpage(
                compat_urlparse.urljoin(url, next_page), playlist_id,
                'Downloading page %d' % page_num, page_num)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        title, description = self._extract_title_and_description(webpage)

        return self.playlist_result(
            self._entries(webpage, url, playlist_id),
            playlist_id, title, description)


class BBCCoUkIPlayerPlaylistBaseIE(InfoExtractor):
    _VALID_URL_TMPL = r'https?://(?:www\.)?bbc\.co\.uk/iplayer/%%s/(?P<id>%s)' % BBCCoUkIE._ID_REGEX

    @staticmethod
    def _get_default(episode, key, default_key='default'):
        return try_get(episode, lambda x: x[key][default_key])

    def _get_description(self, data):
        synopsis = data.get(self._DESCRIPTION_KEY) or {}
        return dict_get(synopsis, ('large', 'medium', 'small'))

    def _fetch_page(self, programme_id, per_page, series_id, page):
        elements = self._get_elements(self._call_api(
            programme_id, per_page, page + 1, series_id))
        for element in elements:
            episode = self._get_episode(element)
            episode_id = episode.get('id')
            if not episode_id:
                continue
            thumbnail = None
            image = self._get_episode_image(episode)
            if image:
                thumbnail = image.replace('{recipe}', 'raw')
            category = self._get_default(episode, 'labels', 'category')
            yield {
                '_type': 'url',
                'id': episode_id,
                'title': self._get_episode_field(episode, 'subtitle'),
                'url': 'https://www.bbc.co.uk/iplayer/episode/' + episode_id,
                'thumbnail': thumbnail,
                'description': self._get_description(episode),
                'categories': [category] if category else None,
                'series': self._get_episode_field(episode, 'title'),
                'ie_key': BBCCoUkIE.ie_key(),
            }

    def _real_extract(self, url):
        pid = self._match_id(url)
        qs = compat_parse_qs(compat_urllib_parse_urlparse(url).query)
        series_id = qs.get('seriesId', [None])[0]
        page = qs.get('page', [None])[0]
        per_page = 36 if page else self._PAGE_SIZE
        fetch_page = functools.partial(self._fetch_page, pid, per_page, series_id)
        entries = fetch_page(int(page) - 1) if page else OnDemandPagedList(fetch_page, self._PAGE_SIZE)
        playlist_data = self._get_playlist_data(self._call_api(pid, 1))
        return self.playlist_result(
            entries, pid, self._get_playlist_title(playlist_data),
            self._get_description(playlist_data))


class BBCCoUkIPlayerEpisodesIE(BBCCoUkIPlayerPlaylistBaseIE):
    IE_NAME = 'bbc.co.uk:iplayer:episodes'
    _VALID_URL = BBCCoUkIPlayerPlaylistBaseIE._VALID_URL_TMPL % 'episodes'
    _TESTS = [{
        'url': 'http://www.bbc.co.uk/iplayer/episodes/b05rcz9v',
        'info_dict': {
            'id': 'b05rcz9v',
            'title': 'The Disappearance',
            'description': 'md5:58eb101aee3116bad4da05f91179c0cb',
        },
        'playlist_mincount': 8,
    }, {
        # all seasons
        'url': 'https://www.bbc.co.uk/iplayer/episodes/b094m5t9/doctor-foster',
        'info_dict': {
            'id': 'b094m5t9',
            'title': 'Doctor Foster',
            'description': 'md5:5aa9195fad900e8e14b52acd765a9fd6',
        },
        'playlist_mincount': 10,
    }, {
        # explicit season
        'url': 'https://www.bbc.co.uk/iplayer/episodes/b094m5t9/doctor-foster?seriesId=b094m6nv',
        'info_dict': {
            'id': 'b094m5t9',
            'title': 'Doctor Foster',
            'description': 'md5:5aa9195fad900e8e14b52acd765a9fd6',
        },
        'playlist_mincount': 5,
    }, {
        # all pages
        'url': 'https://www.bbc.co.uk/iplayer/episodes/m0004c4v/beechgrove',
        'info_dict': {
            'id': 'm0004c4v',
            'title': 'Beechgrove',
            'description': 'Gardening show that celebrates Scottish horticulture and growing conditions.',
        },
        'playlist_mincount': 37,
    }, {
        # explicit page
        'url': 'https://www.bbc.co.uk/iplayer/episodes/m0004c4v/beechgrove?page=2',
        'info_dict': {
            'id': 'm0004c4v',
            'title': 'Beechgrove',
            'description': 'Gardening show that celebrates Scottish horticulture and growing conditions.',
        },
        'playlist_mincount': 1,
    }]
    _PAGE_SIZE = 100
    _DESCRIPTION_KEY = 'synopsis'

    def _get_episode_image(self, episode):
        return self._get_default(episode, 'image')

    def _get_episode_field(self, episode, field):
        return self._get_default(episode, field)

    @staticmethod
    def _get_elements(data):
        return data['entities']['results']

    @staticmethod
    def _get_episode(element):
        return element.get('episode') or {}

    def _call_api(self, pid, per_page, page=1, series_id=None):
        variables = {
            'id': pid,
            'page': page,
            'perPage': per_page,
        }
        if series_id:
            variables['sliceId'] = series_id
        return self._download_json(
            'https://graph.ibl.api.bbc.co.uk/', pid, headers={
                'Content-Type': 'application/json'
            }, data=json.dumps({
                'id': '5692d93d5aac8d796a0305e895e61551',
                'variables': variables,
            }).encode('utf-8'))['data']['programme']

    @staticmethod
    def _get_playlist_data(data):
        return data

    def _get_playlist_title(self, data):
        return self._get_default(data, 'title')


class BBCCoUkIPlayerGroupIE(BBCCoUkIPlayerPlaylistBaseIE):
    IE_NAME = 'bbc.co.uk:iplayer:group'
    _VALID_URL = BBCCoUkIPlayerPlaylistBaseIE._VALID_URL_TMPL % 'group'
    _TESTS = [{
        # Available for over a year unlike 30 days for most other programmes
        'url': 'http://www.bbc.co.uk/iplayer/group/p02tcc32',
        'info_dict': {
            'id': 'p02tcc32',
            'title': 'Bohemian Icons',
            'description': 'md5:683e901041b2fe9ba596f2ab04c4dbe7',
        },
        'playlist_mincount': 10,
    }, {
        # all pages
        'url': 'https://www.bbc.co.uk/iplayer/group/p081d7j7',
        'info_dict': {
            'id': 'p081d7j7',
            'title': 'Music in Scotland',
            'description': 'Perfomances in Scotland and programmes featuring Scottish acts.',
        },
        'playlist_mincount': 47,
    }, {
        # explicit page
        'url': 'https://www.bbc.co.uk/iplayer/group/p081d7j7?page=2',
        'info_dict': {
            'id': 'p081d7j7',
            'title': 'Music in Scotland',
            'description': 'Perfomances in Scotland and programmes featuring Scottish acts.',
        },
        'playlist_mincount': 11,
    }]
    _PAGE_SIZE = 200
    _DESCRIPTION_KEY = 'synopses'

    def _get_episode_image(self, episode):
        return self._get_default(episode, 'images', 'standard')

    def _get_episode_field(self, episode, field):
        return episode.get(field)

    @staticmethod
    def _get_elements(data):
        return data['elements']

    @staticmethod
    def _get_episode(element):
        return element

    def _call_api(self, pid, per_page, page=1, series_id=None):
        return self._download_json(
            'http://ibl.api.bbc.co.uk/ibl/v1/groups/%s/episodes' % pid,
            pid, query={
                'page': page,
                'per_page': per_page,
            })['group_episodes']

    @staticmethod
    def _get_playlist_data(data):
        return data['group']

    def _get_playlist_title(self, data):
        return data.get('title')


class BBCCoUkPlaylistIE(BBCCoUkPlaylistBaseIE):
    IE_NAME = 'bbc.co.uk:playlist'
    _VALID_URL = r'https?://(?:www\.)?bbc\.co\.uk/programmes/(?P<id>%s)/(?:episodes|broadcasts|clips)' % BBCCoUkIE._ID_REGEX
    _URL_TEMPLATE = 'http://www.bbc.co.uk/programmes/%s'
    _VIDEO_ID_TEMPLATE = r'data-pid=["\'](%s)'
    _TESTS = [{
        'url': 'http://www.bbc.co.uk/programmes/b05rcz9v/clips',
        'info_dict': {
            'id': 'b05rcz9v',
            'title': 'The Disappearance - Clips - BBC Four',
            'description': 'French thriller serial about a missing teenager.',
        },
        'playlist_mincount': 7,
    }, {
        # multipage playlist, explicit page
        'url': 'http://www.bbc.co.uk/programmes/b00mfl7n/clips?page=1',
        'info_dict': {
            'id': 'b00mfl7n',
            'title': 'Frozen Planet - Clips - BBC One',
            'description': 'md5:65dcbf591ae628dafe32aa6c4a4a0d8c',
        },
        'playlist_mincount': 24,
    }, {
        # multipage playlist, all pages
        'url': 'http://www.bbc.co.uk/programmes/b00mfl7n/clips',
        'info_dict': {
            'id': 'b00mfl7n',
            'title': 'Frozen Planet - Clips - BBC One',
            'description': 'md5:65dcbf591ae628dafe32aa6c4a4a0d8c',
        },
        'playlist_mincount': 142,
    }, {
        'url': 'http://www.bbc.co.uk/programmes/b05rcz9v/broadcasts/2016/06',
        'only_matching': True,
    }, {
        'url': 'http://www.bbc.co.uk/programmes/b05rcz9v/clips',
        'only_matching': True,
    }, {
        'url': 'http://www.bbc.co.uk/programmes/b055jkys/episodes/player',
        'only_matching': True,
    }]

    def _extract_title_and_description(self, webpage):
        title = self._og_search_title(webpage, fatal=False)
        description = self._og_search_description(webpage)
        return title, description
