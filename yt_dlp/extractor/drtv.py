import binascii
import hashlib
import json
import re
import uuid

from .common import InfoExtractor
from ..aes import aes_cbc_decrypt_bytes, unpad_pkcs7
from ..compat import compat_etree_fromstring, compat_urllib_parse_unquote
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    mimetype2ext,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    update_url_query,
    url_or_none,
)

SERIES_API = 'https://production-cdn.dr-massive.com/api/page?device=web_browser&item_detail_expand=all&lang=da&max_list_prefetch=3&path=%s'

class DRTVIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:www\.)?dr\.dk/(?:tv/se|nyheder|(?P<radio>radio|lyd)(?:/ondemand)?)/(?:[^/]+/)*|
                            (?:www\.)?(?:dr\.dk|dr-massive\.com)/drtv/(?:se|episode|program)/
                        )
                        (?P<id>[\da-z_-]+)
                    '''
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['DK']
    IE_NAME = 'drtv'
    _TESTS = [{
        'url': 'https://www.dr.dk/tv/se/boern/ultra/klassen-ultra/klassen-darlig-taber-10',
        'md5': '25e659cccc9a2ed956110a299fdf5983',
        'info_dict': {
            'id': 'klassen-darlig-taber-10',
            'ext': 'mp4',
            'title': 'Klassen - Dårlig taber (10)',
            'description': 'md5:815fe1b7fa656ed80580f31e8b3c79aa',
            'timestamp': 1539085800,
            'upload_date': '20181009',
            'duration': 606.84,
            'series': 'Klassen',
            'season': 'Klassen I',
            'season_number': 1,
            'season_id': 'urn:dr:mu:bundle:57d7e8216187a4031cfd6f6b',
            'episode': 'Episode 10',
            'episode_number': 10,
            'release_year': 2016,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
        'skip': 'this video has been removed',
    }, {
        # embed
        'url': 'https://www.dr.dk/nyheder/indland/live-christianias-rydning-af-pusher-street-er-i-gang',
        'info_dict': {
            'id': 'urn:dr:mu:programcard:57c926176187a50a9c6e83c6',
            'ext': 'mp4',
            'title': 'christiania pusher street ryddes drdkrjpo',
            'description': 'md5:2a71898b15057e9b97334f61d04e6eb5',
            'timestamp': 1472800279,
            'upload_date': '20160902',
            'duration': 131.4,
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        # with SignLanguage formats
        'url': 'https://www.dr.dk/tv/se/historien-om-danmark/-/historien-om-danmark-stenalder',
        'info_dict': {
            'id': '00831690010',
            'ext': 'mp4',
            'title': 'Historien om Danmark: Stenalder',
            'description': 'md5:8c66dcbc1669bbc6f873879880f37f2a',
            'timestamp': 1546628400,
            'upload_date': '20190104',
            'duration': 3504.619,
            'formats': 'mincount:20',
            'release_year': 2017,
            'season_id': 'urn:dr:mu:bundle:5afc03ad6187a4065ca5fd35',
            'season_number': 1,
            'season': 'Historien om Danmark',
            'series': 'Historien om Danmark',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.dr.dk/lyd/p4kbh/regionale-nyheder-kh4/p4-nyheder-2019-06-26-17-30-9',
        'only_matching': True,
    }, {
        'url': 'https://www.dr.dk/drtv/se/bonderoeven_71769',
        'info_dict': {
            'id': '00951930010',
            'ext': 'mp4',
            'title': 'Bonderøven 2019 (1:8)',
            'description': 'md5:b6dcfe9b6f0bea6703e9a0092739a5bd',
            'timestamp': 1654856100,
            'upload_date': '20220610',
            'duration': 2576.6,
            'season': 'Bonderøven 2019',
            'season_id': 'urn:dr:mu:bundle:5c201667a11fa01ca4528ce5',
            'release_year': 2019,
            'season_number': 2019,
            'series': 'Frank & Kastaniegaarden',
            'episode_number': 1,
            'episode': 'Episode 1',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.dr.dk/drtv/episode/bonderoeven_71769',
        'only_matching': True,
    }, {
        'url': 'https://dr-massive.com/drtv/se/bonderoeven_71769',
        'only_matching': True,
    }, {
        'url': 'https://www.dr.dk/drtv/program/jagten_220924',
        'only_matching': True,
    }, {
        'url': 'https://www.dr.dk/lyd/p4aarhus/regionale-nyheder-ar4/regionale-nyheder-2022-05-05-12-30-3',
        'info_dict': {
            'id': 'urn:dr:mu:programcard:6265cb2571401424d0360113',
            'title': "Regionale nyheder",
            'ext': 'mp4',
            'duration': 120.043,
            'series': 'P4 Østjylland regionale nyheder',
            'timestamp': 1651746600,
            'season': 'Regionale nyheder',
            'release_year': 0,
            'season_id': 'urn:dr:mu:bundle:61c26889539f0201586b73c5',
            'description': '',
            'upload_date': '20220505',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'this video has been removed',
    }, {
        'url': 'https://www.dr.dk/lyd/p4kbh/regionale-nyheder-kh4/regionale-nyheder-2023-03-14-10-30-9',
        'info_dict': {
            'ext': 'mp4',
            'id': '14802310112',
            'timestamp': 1678786200,
            'duration': 120.043,
            'season_id': 'urn:dr:mu:bundle:63a4f7c87140143504b6710f',
            'series': 'P4 København regionale nyheder',
            'upload_date': '20230314',
            'release_year': 0,
            'description': 'Hør seneste regionale nyheder fra P4 København.',
            'season': 'Regionale nyheder',
            'title': 'Regionale nyheder',
        },
    }]

    def _real_extract(self, url):
        raw_video_id, is_radio_url = self._match_valid_url(url).group('id', 'radio')
        webpage = self._download_webpage(url, raw_video_id)
        if '>Programmet er ikke længere tilgængeligt' in webpage:
            raise ExtractorError(
                'Video %s is not available' % raw_video_id, expected=True)
        json_data = self._search_json(r'window\.__data\s*=', webpage, 'data', raw_video_id)
        item = traverse_obj(json_data, ('cache', 'page', Ellipsis, (None, ('entries', 0)), 'item'), get_all=False)
        itemId = item.get('id')
        videoId = item['customId'].split(':')[-1]
        deviceId = uuid.uuid1()
        token = self._download_json('https://isl.dr-massive.com/api/authorization/anonymous-sso?device=web_browser&ff=idp%2Cldp&lang=da', videoId, headers={'Content-Type': 'application/json'}, data=json.dumps({'deviceId': str(deviceId), 'scopes': ['Catalog'], 'optout': True}).encode('utf-8'))[0]['value']
        data = self._download_json('https://production.dr-massive.com/api/account/items/{0}/videos?delivery=stream&device=web_browser&ff=idp%2Cldp%2Crpt&lang=da&resolution=HD-1080&sub=Anonymous'.format(itemId), videoId, headers={'authorization': 'Bearer {0}'.format(token)})
        formats = []
        subtitles = {}
        for fmt in data:
            format_id = fmt.get('format', 'na')
            access_service = fmt.get('accessService')
            preference = None
            if accessService in ('SpokenSubtitles', 'SignLanguage', 'VisuallyInterpreted'):
                preference = -1
                formatId += '-%s' % accessService
            elif accessService == 'StandardVideo':
                preference = 1
            fmts, subs = self._extract_m3u8_formats_and_subtitles(fmt['url'], videoId, 'mp4', entry_protocol='m3u8_native', preference=preference, m3u8_id=formatId, fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
            LANGS = {
                'Danish': 'da',
            }
            for subs in fmt['subtitles']:
                if not isinstance(subs, dict):
                    continue
                sub_uri = url_or_none(subs.get('link'))
                if not sub_uri:
                    continue
                lang = subs.get('language') or 'da'
                subtitles.setdefault(LANGS.get(lang, lang), []).append({
                    'url': sub_uri,
                    'ext': mimetype2ext(subs.get('format')) or 'vtt'
                })
            
        return {
            'id': videoId,
            'title': item.get('episodeName'),
            'description': item.get('description'),
            'formats': formats,
            'subtitles': subtitles,
        }

class DRTVLiveIE(InfoExtractor):
    IE_NAME = 'drtv:live'
    _VALID_URL = r'https?://(?:www\.)?dr\.dk/(?:tv|TV)/live/(?P<id>[\da-z-]+)'
    _GEO_COUNTRIES = ['DK']
    _TEST = {
        'url': 'https://www.dr.dk/tv/live/dr1',
        'info_dict': {
            'id': 'dr1',
            'ext': 'mp4',
            'title': 're:^DR1 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        channel_data = self._download_json(
            'https://www.dr.dk/mu-online/api/1.0/channel/' + channel_id,
            channel_id)
        title = channel_data['Title']

        formats = []
        for streaming_server in channel_data.get('StreamingServers', []):
            server = streaming_server.get('Server')
            if not server:
                continue
            link_type = streaming_server.get('LinkType')
            for quality in streaming_server.get('Qualities', []):
                for stream in quality.get('Streams', []):
                    stream_path = stream.get('Stream')
                    if not stream_path:
                        continue
                    stream_url = update_url_query(
                        '%s/%s' % (server, stream_path), {'b': ''})
                    if link_type == 'HLS':
                        formats.extend(self._extract_m3u8_formats(
                            stream_url, channel_id, 'mp4',
                            m3u8_id=link_type, fatal=False, live=True))
                    elif link_type == 'HDS':
                        formats.extend(self._extract_f4m_formats(update_url_query(
                            '%s/%s' % (server, stream_path), {'hdcore': '3.7.0'}),
                            channel_id, f4m_id=link_type, fatal=False))

        return {
            'id': channel_id,
            'title': title,
            'thumbnail': channel_data.get('PrimaryImageUri'),
            'formats': formats,
            'is_live': True,
        }

class DRTVSeasonIE(InfoExtractor):
    IE_NAME = 'drtv:season'
    _VALID_URL = r'https?://(?:www\.)?(?:dr\.dk|dr-massive\.com)/drtv/saeson/(?P<display_id>[\w-]+)_(?P<id>\d+)'
    _GEO_COUNTRIES = ['DK']
    _TESTS = [{
        'url': 'https://www.dr.dk/drtv/saeson/frank-and-kastaniegaarden_9008',
        'info_dict': {
            'id': '9008',
            'display_id': 'frank-and-kastaniegaarden',
            'title': 'Frank & Kastaniegaarden',
            'series': 'Frank & Kastaniegaarden',
        },
        'playlist_mincount': 8
    }, {
        'url': 'https://www.dr.dk/drtv/saeson/frank-and-kastaniegaarden_8761',
        'info_dict': {
            'id': '8761',
            'display_id': 'frank-and-kastaniegaarden',
            'title': 'Frank & Kastaniegaarden',
            'series': 'Frank & Kastaniegaarden',
        },
        'playlist_mincount': 19
    }]

    def _real_extract(self, url):
        display_id, season_id = self._match_valid_url(url).group('display_id', 'id')
        data = self._download_json(SERIES_API % f'/saeson/{display_id}_{season_id}', display_id)

        entries = [{
            '_type': 'url',
            'url': f'https://www.dr.dk/drtv{episode["path"]}',
            'ie_key': DRTVIE.ie_key(),
            'title': episode.get('title'),
            'episode': episode.get('episodeName'),
            'description': episode.get('shortDescription'),
            'series': traverse_obj(data, ('entries', 0, 'item', 'title')),
            'season_number': traverse_obj(data, ('entries', 0, 'item', 'seasonNumber')),
            'episode_number': episode.get('episodeNumber'),
        } for episode in traverse_obj(data, ('entries', 0, 'item', 'episodes', 'items'))]

        return {
            '_type': 'playlist',
            'id': season_id,
            'display_id': display_id,
            'title': traverse_obj(data, ('entries', 0, 'item', 'title')),
            'series': traverse_obj(data, ('entries', 0, 'item', 'title')),
            'entries': entries,
            'season_number': traverse_obj(data, ('entries', 0, 'item', 'seasonNumber'))
        }


class DRTVSeriesIE(InfoExtractor):
    IE_NAME = 'drtv:series'
    _VALID_URL = r'https?://(?:www\.)?(?:dr\.dk|dr-massive\.com)/drtv/serie/(?P<display_id>[\w-]+)_(?P<id>\d+)'
    _GEO_COUNTRIES = ['DK']
    _TESTS = [{
        'url': 'https://www.dr.dk/drtv/serie/frank-and-kastaniegaarden_6954',
        'info_dict': {
            'id': '6954',
            'display_id': 'frank-and-kastaniegaarden',
            'title': 'Frank & Kastaniegaarden',
            'series': 'Frank & Kastaniegaarden',
        },
        'playlist_mincount': 15
    }]

    def _real_extract(self, url):
        display_id, series_id = self._match_valid_url(url).group('display_id', 'id')
        data = self._download_json(SERIES_API % f'/serie/{display_id}_{series_id}', display_id)

        entries = [{
            '_type': 'url',
            'url': f'https://www.dr.dk/drtv{season.get("path")}',
            'ie_key': DRTVSeasonIE.ie_key(),
            'title': season.get('title'),
            'series': traverse_obj(data, ('entries', 0, 'item', 'title')),
            'season_number': traverse_obj(data, ('entries', 0, 'item', 'seasonNumber'))
        } for season in traverse_obj(data, ('entries', 0, 'item', 'show', 'seasons', 'items'))]

        return {
            '_type': 'playlist',
            'id': series_id,
            'display_id': display_id,
            'title': traverse_obj(data, ('entries', 0, 'item', 'title')),
            'series': traverse_obj(data, ('entries', 0, 'item', 'title')),
            'entries': entries
        }
