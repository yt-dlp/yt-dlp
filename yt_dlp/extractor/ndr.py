# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    parse_duration,
    qualities,
    try_get,
    unified_strdate,
    urljoin,
)


class NDRBaseIE(InfoExtractor):
    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        self.BASE_URL = mobj.group('base_url')
        display_id = next(group for group in mobj.groups()[1:] if group)
        id = mobj.group('id')
        webpage = self._download_webpage(url, display_id)
        return self._extract_embed(webpage, display_id, id)


class NDRIE(NDRBaseIE):
    IE_NAME = 'ndr'
    IE_DESC = 'NDR.de - Norddeutscher Rundfunk'
    _VALID_URL = r'(?P<base_url>https?://(?:www\.)?(?:daserste\.)?ndr\.de)/(?:[^/]+/)*(?P<display_id>[^/?#]+),(?P<id>[\da-z]+)\.html'
    _TESTS = [{  # Content removed
        'url': 'http://www.ndr.de/fernsehen/Party-Poette-und-Parade,hafengeburtstag988.html',
        'only_matching': True
    }, {
        'url': 'https://www.ndr.de/sport/fussball/Rostocks-Matchwinner-Froede-Ein-Hansa-Debuet-wie-im-Maerchen,hansa10312.html',
        'only_matching': True
    }, {
        'url': 'https://www.ndr.de/nachrichten/niedersachsen/kommunalwahl_niedersachsen_2021/Grosse-Parteien-zufrieden-mit-Ergebnissen-der-Kommunalwahl,kommunalwahl1296.html',
        'info_dict': {
            'id': 'kommunalwahl1296',
            'ext': 'mp4',
            'title': 'Die Spitzenrunde: Die Wahl aus Sicht der Landespolitik',
            'thumbnail': 'https://www.ndr.de/fernsehen/screenshot1194912_v-contentxl.jpg',
            'description': 'md5:5c6e2ad744cef499135735a1036d7aa7',
            'series': 'Hallo Niedersachsen',
            'channel': 'NDR Fernsehen',
            'upload_date': '20210913',
            'duration': 438,
        },
    }, {
        'url': 'https://www.ndr.de/fernsehen/sendungen/extra_3/extra-3-Satiremagazin-mit-Christian-Ehring,sendung1091858.html',
        'info_dict': {
            'id': 'sendung1091858',
            'ext': 'mp4',
            'title': 'Extra 3 vom 11.11.2020 mit Christian Ehring',
            'thumbnail': 'https://www.ndr.de/fernsehen/screenshot983938_v-contentxl.jpg',
            'description': 'md5:700f6de264010585012a72f97b0ac0c9',
            'series': 'extra 3',
            'channel': 'NDR Fernsehen',
            'upload_date': '20201111',
            'duration': 1749,
        }
    }, {
        'url': 'http://www.ndr.de/info/La-Valette-entgeht-der-Hinrichtung,audio51535.html',
        'info_dict': {
            'id': 'audio51535',
            'ext': 'mp3',
            'title': 'La Valette entgeht der Hinrichtung',
            'thumbnail': 'https://www.ndr.de/mediathek/mediathekbild140_v-podcast.jpg',
            'description': 'md5:22f9541913a40fe50091d5cdd7c9f536',
            'upload_date': '20140729',
            'duration': 884.0,
        },
        'expected_warnings': ['unable to extract json url'],
    }, {
        'url': 'https://daserste.ndr.de/panorama/archiv/2022/Das-Ende-des-Schnitzels,schnitzel236.html',
        'info_dict': {
            'id': 'schnitzel236',
            'ext': 'mp4',
            'title': 'Das Ende des Schnitzels?',
            'description': 'md5:e99ca7451260f172fc6a60cd59ac3d77',
            'thumbnail': 'https://daserste.ndr.de/panorama/schweineschnitzel112_v-contentxl.jpg',
            'series': 'Panorama',
            'channel': 'Das Erste',
            'upload_date': '20220113',
            'duration': 1768
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.ndr.de/fernsehen/sendungen/visite/Gallensteine-Ursachen-Symptome-und-Behandlung,visite21048.html',
        'md5': 'ae57f80511c1e1f2fd0d0d3d31aeae7c',
        'info_dict': {
            'id': 'visite21048',
            'ext': 'mp4',
            'title': 'Gallensteine: Ursachen, Symptome und Behandlung',
            'upload_date': '20220301',
            'duration': 359,
            'thumbnail': 'https://www.ndr.de/gallensteine116_v-contentxl.jpg',
            'series': 'Visite',
            'channel': 'NDR Fernsehen',
            'description': 'md5:026ca736d4506de0e3e6f561336174ee',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _extract_embed(self, webpage, display_id, id):
        formats = []
        json_url = self._search_regex(r'<iframe[^>]+src=\"([^\"]+)_theme-[^\.]*\.html\"', webpage,
                                      'json url', fatal=False)
        if json_url:
            data_json = self._download_json(self.BASE_URL + json_url.replace('ardplayer_image', 'ardjson_image') + '.json',
                                            id, fatal=False)
            info_json = data_json.get('_info', {})
            media_json = try_get(data_json, lambda x: x['_mediaArray'][0]['_mediaStreamArray'])
            for media in media_json:
                if media.get('_quality') == 'auto':
                    formats.extend(self._extract_m3u8_formats(media['_stream'], id))
            subtitles = {}
            sub_url = data_json.get('_subtitleUrl')
            if sub_url:
                subtitles.setdefault('de', []).append({
                    'url': self.BASE_URL + sub_url,
                })
            self._sort_formats(formats)
            return {
                'id': id,
                'title': info_json.get('clipTitle'),
                'thumbnail': self.BASE_URL + data_json.get('_previewImage'),
                'description': info_json.get('clipDescription'),
                'series': info_json.get('seriesTitle') or None,
                'channel': info_json.get('channelTitle'),
                'upload_date': unified_strdate(info_json.get('clipDate')),
                'duration': data_json.get('_duration'),
                'formats': formats,
                'subtitles': subtitles,
            }
        else:
            json_url = self.BASE_URL + self._search_regex(r'apiUrl\s?=\s?\'([^\']+)\'', webpage, 'json url').replace(
                '_belongsToPodcast-', '')
            data_json = self._download_json(json_url, id, fatal=False)
            return {
                'id': id,
                'title': data_json.get('title'),
                'thumbnail': self.BASE_URL + data_json.get('poster'),
                'description': data_json.get('summary'),
                'upload_date': unified_strdate(data_json.get('publicationDate')),
                'duration': parse_duration(data_json.get('duration')),
                'formats': [{
                    'url': try_get(data_json, (lambda x: x['audio'][0]['url'], lambda x: x['files'][0]['url'])),
                    'vcodec': 'none',
                    'ext': 'mp3',
                }],
            }


class NJoyIE(NDRBaseIE):
    IE_NAME = 'njoy'
    IE_DESC = 'N-JOY'
    _VALID_URL = r'(?P<base_url>https?://(?:www\.)?n-joy\.de)/(?:[^/]+/)*(?:(?P<display_id>[^/?#]+),)?(?P<id>[\da-z]+)\.html'
    _TESTS = [{
        'url': 'https://www.n-joy.de/leben/Der-N-JOY-Heartbeat-Der-Song-mit-dem-ihr-Leben-rettet,heartbeat108.html',
        'info_dict': {
            'id': 'herzdruckmassage106',
            'ext': 'mp4',
            'title': 'Lasst uns Leben retten: So funktioniert die Herzdruckmassage',
            'description': None,
            'uploader': 'njoy',
            'upload_date': '20220302',
            'duration': 167,
            'display_id': 'Der-N-JOY-Heartbeat-Der-Song-mit-dem-ihr-Leben-rettet',
            'thumbnail': 'https://www.n-joy.de/leben/erstehilfe370_v-contentxl.jpg'},
        'params': {'skip_download': True},
        'expected_warnings': ['unable to extract description'],
    }, {
        # Removed
        'url': 'http://www.n-joy.de/entertainment/comedy/comedy_contest/Benaissa-beim-NDR-Comedy-Contest,comedycontest2480.html',
        'only_matching': True
    }, {
        # Removed
        'url': 'http://www.n-joy.de/musik/Das-frueheste-DJ-Set-des-Nordens-live-mit-Felix-Jaehn-,felixjaehn168.html',
        'only_matching': True
    }, {
        'url': 'http://www.n-joy.de/radio/webradio/morningshow209.html',
        'only_matching': True,
    }]

    def _extract_embed(self, webpage, display_id, id):
        video_id = self._search_regex(
            r'<iframe[^>]+id="pp_([\da-z]+)"', webpage, 'embed id')
        description = self._search_regex(
            r'<div[^>]+class="subline"[^>]*>[^<]+</div>\s*<p>([^<]+)</p>',
            webpage, 'description', fatal=False)
        return {
            '_type': 'url_transparent',
            'ie_key': 'NDREmbedBase',
            'url': 'ndr:%s' % video_id,
            'display_id': display_id,
            'description': description,
        }


class NDREmbedBaseIE(InfoExtractor):
    IE_NAME = 'ndr:embed:base'
    _VALID_URL = r'(?:ndr:(?P<id_s>[\da-z]+)|https?://www\.ndr\.de/(?P<id>[\da-z]+)-ppjson\.json)'
    _TESTS = [{
        'url': 'ndr:soundcheck3366',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/soundcheck3366-ppjson.json',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('id_s')

        ppjson = self._download_json(
            'http://www.ndr.de/%s-ppjson.json' % video_id, video_id)

        playlist = ppjson['playlist']

        formats = []
        quality_key = qualities(('xs', 's', 'm', 'l', 'xl'))

        for format_id, f in playlist.items():
            src = f.get('src')
            if not src:
                continue
            ext = determine_ext(src, None)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    src, video_id, 'mp4', m3u8_id='hls',
                    entry_protocol='m3u8_native', fatal=False))
            else:
                quality = f.get('quality')
                ff = {
                    'url': src,
                    'format_id': quality or format_id,
                    'quality': quality_key(quality),
                }
                type_ = f.get('type')
                if type_ and type_.split('/')[0] == 'audio':
                    ff['vcodec'] = 'none'
                    ff['ext'] = ext or 'mp3'
                formats.append(ff)
        self._sort_formats(formats)

        config = playlist['config']

        live = playlist.get('config', {}).get('streamType') in ['httpVideoLive', 'httpAudioLive']
        title = config['title']
        uploader = ppjson.get('config', {}).get('branding')
        upload_date = ppjson.get('config', {}).get('publicationDate')
        duration = int_or_none(config.get('duration'))

        thumbnails = []
        poster = try_get(config, lambda x: x['poster'], dict) or {}
        for thumbnail_id, thumbnail in poster.items():
            thumbnail_url = urljoin(url, thumbnail.get('src'))
            if not thumbnail_url:
                continue
            thumbnails.append({
                'id': thumbnail.get('quality') or thumbnail_id,
                'url': thumbnail_url,
                'preference': quality_key(thumbnail.get('quality')),
            })

        subtitles = {}
        tracks = config.get('tracks')
        if tracks and isinstance(tracks, list):
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                track_url = urljoin(url, track.get('src'))
                if not track_url:
                    continue
                subtitles.setdefault(track.get('srclang') or 'de', []).append({
                    'url': track_url,
                    'ext': 'ttml',
                })

        return {
            'id': video_id,
            'title': title,
            'is_live': live,
            'uploader': uploader if uploader != '-' else None,
            'upload_date': upload_date[0:8] if upload_date else None,
            'duration': duration,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }


class NDREmbedIE(NDREmbedBaseIE):
    IE_NAME = 'ndr:embed'
    _VALID_URL = r'https?://(?:www\.)?(?:daserste\.)?ndr\.de/(?:[^/]+/)*(?P<id>[\da-z]+)-(?:player|externalPlayer)\.html'
    _TESTS = [{  # Removed
        'url': 'http://www.ndr.de/fernsehen/sendungen/ndr_aktuell/ndraktuell28488-player.html',
        'only_matching': True
    }, {
        'url': 'http://www.ndr.de/ndr2/events/soundcheck/soundcheck3366-player.html',
        'only_matching': True
    }, {
        'url': 'http://www.ndr.de/info/audio51535-player.html',
        'md5': 'bb3cd38e24fbcc866d13b50ca59307b8',
        'info_dict': {
            'id': 'audio51535',
            'ext': 'mp3',
            'title': 'La Valette entgeht der Hinrichtung',
            'is_live': False,
            'uploader': 'ndrinfo',
            'upload_date': '20210915',
            'duration': 884,
            'thumbnail': 'http://www.ndr.de/common/resources/images/mediathek/default-audio-image.png',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Removed
        'url': 'http://www.ndr.de/fernsehen/livestream/livestream217-externalPlayer.html',
        'only_matching': True
    }, {
        'url': 'http://www.ndr.de/ndrkultur/audio255020-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/fernsehen/sendungen/nordtour/nordtour7124-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/kultur/film/videos/videoimport10424-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/fernsehen/sendungen/hamburg_journal/hamj43006-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/fernsehen/sendungen/weltbilder/weltbilder4518-player.html',
        'only_matching': True,
    }, {
        'url': 'http://www.ndr.de/fernsehen/doku952-player.html',
        'only_matching': True,
    }]


class NJoyEmbedIE(NDREmbedBaseIE):
    IE_NAME = 'njoy:embed'
    _VALID_URL = r'https?://(?:www\.)?n-joy\.de/(?:[^/]+/)*(?P<id>[\da-z]+)-(?:player|externalPlayer)_[^/]+\.html'
    _TESTS = [{
        # httpVideo
        'url': 'http://www.n-joy.de/events/reeperbahnfestival/doku948-player_image-bc168e87-5263-4d6d-bd27-bb643005a6de_theme-n-joy.html',
        'md5': '8483cbfe2320bd4d28a349d62d88bd74',
        'info_dict': {
            'id': 'doku948',
            'ext': 'mp4',
            'title': 'Zehn Jahre Reeperbahn Festival - die Doku',
            'is_live': False,
            'upload_date': '20200826',
            'duration': 1011,
            'thumbnail': 'https://www.n-joy.de/events/reeperbahnfestival/reeperbahnfestival1151_v-contentxl.jpg',
        },
    }, {
        # Removed
        'url': 'http://www.n-joy.de/news_wissen/stefanrichter100-player_image-d5e938b1-f21a-4b9a-86b8-aaba8bca3a13_theme-n-joy.html',
        'only_matching': True
    }, {
        # httpAudioLive, no explicit ext
        'url': 'http://www.n-joy.de/news_wissen/webradioweltweit100-player_image-3fec0484-2244-4565-8fb8-ed25fd28b173_theme-n-joy.html',
        'info_dict': {
            'id': 'webradioweltweit100',
            'ext': 'mp3',
            'title': r're:^N-JOY Weltweit \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'is_live': True,
            'uploader': 'njoy',
            'upload_date': '20210830',
            'live_status': 'is_live',
            'thumbnail': 'https://www.n-joy.de/entertainment/globus112_v-contentxl.jpg',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.n-joy.de/musik/dockville882-player_image-3905259e-0803-4764-ac72-8b7de077d80a_theme-n-joy.html',
        'only_matching': True,
    }, {
        'url': 'http://www.n-joy.de/radio/sendungen/morningshow/urlaubsfotos190-player_image-066a5df1-5c95-49ec-a323-941d848718db_theme-n-joy.html',
        'only_matching': True,
    }, {
        'url': 'http://www.n-joy.de/entertainment/comedy/krudetv290-player_image-ab261bfe-51bf-4bf3-87ba-c5122ee35b3d_theme-n-joy.html',
        'only_matching': True,
    }]
