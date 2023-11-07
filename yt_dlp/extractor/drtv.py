import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    mimetype2ext,
    parse_iso8601,
    random_uuidv4,
    try_call,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj

SERIES_API = 'https://production-cdn.dr-massive.com/api/page?device=web_browser&item_detail_expand=all&lang=da&max_list_prefetch=3&path=%s'


class DRTVIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:www\.)?dr\.dk/tv/se(?:/ondemand)?/(?:[^/]+/)*|
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
        'skip': 'this video has been removed',
    }, {
        'url': 'https://www.dr.dk/drtv/se/bonderoeven_71769',
        'info_dict': {
            'id': '00951930010',
            'ext': 'mp4',
            'title': 'Frank & Kastaniegaarden',
            'description': 'md5:974e1780934cf3275ef10280204bccb0',
            'release_timestamp': 1546545600,
            'release_date': '20190103',
            'duration': 2576,
            'season': 'Frank & Kastaniegaarden',
            'season_id': '67125',
            'release_year': 2019,
            'season_number': 2019,
            'series': 'Frank & Kastaniegaarden',
            'episode_number': 1,
            'episode': 'Frank & Kastaniegaarden',
            'thumbnail': r're:https?://.+',
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
    }]

    _TOKEN = None

    def _real_initialize(self):
        if self._TOKEN:
            return
        token_response = self._download_json(
            'https://production.dr-massive.com/api/authorization/anonymous-sso', None,
            note='Downloading anonymous token', headers={
                'content-type': 'application/json',
            },
            query={
                'device': 'web_browser',
                'ff': 'idp,ldp,rpt',
                'lang': 'da',
                'supportFallbackToken': 'true',
            },
            data=json.dumps({
                'deviceId': random_uuidv4(),
                'scopes': [
                    'Catalog',
                ],
                'optout': True,
            }).encode())

        self._TOKEN = traverse_obj(
            token_response, (lambda _, x: x['type'] == 'UserAccount', 'value'), get_all=False)

    def _real_extract(self, url):
        url_slug = self._match_id(url)
        webpage = self._download_webpage(url, url_slug)

        json_data = self._search_json(r'window\.__data\s*=\s*', webpage, 'data', url_slug, fatal=False) or {}
        item = traverse_obj(json_data, ('cache', 'page', ..., (None, ('entries', 0)), 'item'), get_all=False)
        if item:
            item_id = item.get('id')
        else:
            item_id = url_slug.rsplit('_', 1)[-1]
            item = self._download_json(
                f'https://production-cdn.dr-massive.com/api/items/{item_id}', item_id,
                note='Attempting to download backup item data', query={
                    'device': 'web_browser',
                    'expand': 'all',
                    'ff': 'idp,ldp,rpt',
                    'geoLocation': 'dk',
                    'isDeviceAbroad': 'false',
                    'lang': 'da',
                    'segments': 'drtv,optedout',
                    'sub': 'Anonymous',
                })

        video_id = try_call(lambda: item['customId'].split(':')[-1]) or item_id
        stream_data = self._download_json(
            f'https://production.dr-massive.com/api/account/items/{item_id}/videos', video_id,
            note='Downloading stream data', query={
                'delivery': 'stream',
                'device': 'web_browser',
                'ff': 'idp,ldp,rpt',
                'lang': 'da',
                'resolution': 'HD-1080',
                'sub': 'Anonymous',
            },
            headers={
                'authorization': f'Bearer {self._TOKEN}',
            })

        formats = []
        subtitles = {}
        for fmt in stream_data:
            format_id = fmt.get('format', 'na')
            access_service = fmt.get('accessService')
            preference = None
            if access_service in ('SpokenSubtitles', 'SignLanguage', 'VisuallyInterpreted'):
                preference = -1
                format_id += f'-{access_service}'
            elif access_service == 'StandardVideo':
                preference = 1
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                fmt.get('url'), video_id, preference=preference, m3u8_id=format_id, fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
            LANGS = {
                'DanishLanguageSubtitles': 'da',
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
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(item, {
                'title': 'title',
                'description': 'description',
                'thumbnail': ('images', 'wallpaper'),
                'release_timestamp': ('customFields', 'BroadcastTimeDK', {parse_iso8601}),
                'duration': 'duration',
                'series': ('season', 'show', 'title'),
                'season': ('season', 'title'),
                'season_number': ('season', 'seasonNumber', {int_or_none}),
                'season_id': 'seasonId',
                'episode': 'episodeName',
                'episode_number': ('episodeNumber', {int_or_none}),
                'release_year': 'releaseYear',
            }),
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
