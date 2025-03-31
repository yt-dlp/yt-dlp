from .common import InfoExtractor
from ..utils import (
    int_or_none,
    orderedSet,
    parse_duration,
    parse_iso8601,
    parse_qs,
    qualities,
    str_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
    xpath_text,
)


class EuropaIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://ec\.europa\.eu/avservices/(?:video/player|audio/audioDetails)\.cfm\?.*?\bref=(?P<id>[A-Za-z0-9-]+)'
    _TESTS = [{
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?ref=I107758',
        'md5': '574f080699ddd1e19a675b0ddf010371',
        'info_dict': {
            'id': 'I107758',
            'ext': 'mp4',
            'title': 'TRADE - Wikileaks on TTIP',
            'description': 'NEW  LIVE EC Midday press briefing of 11/08/2015',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20150811',
            'duration': 34,
            'view_count': int,
            'formats': 'mincount:3',
        },
    }, {
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?sitelang=en&ref=I107786',
        'only_matching': True,
    }, {
        'url': 'http://ec.europa.eu/avservices/audio/audioDetails.cfm?ref=I-109295&sitelang=en',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        playlist = self._download_xml(
            f'http://ec.europa.eu/avservices/video/player/playlist.cfm?ID={video_id}', video_id)

        def get_item(type_, preference):
            items = {}
            for item in playlist.findall(f'./info/{type_}/item'):
                lang, label = xpath_text(item, 'lg', default=None), xpath_text(item, 'label', default=None)
                if lang and label:
                    items[lang] = label.strip()
            for p in preference:
                if items.get(p):
                    return items[p]

        query = parse_qs(url)
        preferred_lang = query.get('sitelang', ('en', ))[0]

        preferred_langs = orderedSet((preferred_lang, 'en', 'int'))

        title = get_item('title', preferred_langs) or video_id
        description = get_item('description', preferred_langs)
        thumbnail = xpath_text(playlist, './info/thumburl', 'thumbnail')
        upload_date = unified_strdate(xpath_text(playlist, './info/date', 'upload date'))
        duration = parse_duration(xpath_text(playlist, './info/duration', 'duration'))
        view_count = int_or_none(xpath_text(playlist, './info/views', 'views'))

        language_preference = qualities(preferred_langs[::-1])

        formats = []
        for file_ in playlist.findall('./files/file'):
            video_url = xpath_text(file_, './url')
            if not video_url:
                continue
            lang = xpath_text(file_, './lg')
            formats.append({
                'url': video_url,
                'format_id': lang,
                'format_note': xpath_text(file_, './lglabel'),
                'language_preference': language_preference(lang),
            })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
        }


class EuroParlWebstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://multimedia\.europarl\.europa\.eu/
        (?P<lang>[^/]*/)?webstreaming/(?:[^_]*_)?(?P<id>[\w-]+)
    '''
    _TESTS = [{
        'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/plenary-session_20220914-0900-PLENARY',
        'md5': '16420ad9c602663759538ac1ca16a8db',
        'info_dict': {
            'id': '20220914-0900-PLENARY',
            'ext': 'mp4',
            'title': 'Plenary session',
            'description': '',
            'duration': 45147,
            'thumbnail': 'https://storage.eup.glcloud.eu/thumbnail/default_thumbnail.png',
            'release_timestamp': 1663139069,
            'release_date': '20220914',
            'modified_timestamp': 1663650921,
            'modified_date': '20220920',
            'live_status': 'was_live',
        },
    }, {
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/euroscola_20221115-1000-SPECIAL-EUROSCOLA',
        'md5': '8b4304f9e15a6e133100248fb55a5dce',
        'info_dict': {
            'ext': 'mp4',
            'id': '20221115-1000-SPECIAL-EUROSCOLA',
            'release_timestamp': 1668502798,
            'title': 'Euroscola',
            'release_date': '20221115',
            'live_status': 'was_live',
            'description': '',
            'duration': 9587,
            'thumbnail': 'https://storage.eup.glcloud.eu/thumbnail/default_thumbnail.png',
            'modified_timestamp': 1668945274,
            'modified_date': '20221120',
        },
    }, {
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/committee-on-culture-and-education_20230301-1130-COMMITTEE-CULT',
        'md5': '0ca01cf33009d866e6f5e1cd3088c10c',
        'info_dict': {
            'id': '20230301-1130-COMMITTEE-CULT',
            'ext': 'mp4',
            'release_date': '20230301',
            'title': 'Committee on Culture and Education',
            'release_timestamp': 1677666641,
            'description': 'Committee on Culture and Education',
            'duration': 1003,
            'thumbnail': 'https://storage.eup.glcloud.eu/thumbnail/default_thumbnail.png',
            'modified_timestamp': 1732475771,
            'modified_date': '20241124',
            'live_status': 'was_live',
        },
    }, {
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/committee-on-environment-public-health-and-food-safety_20230524-0900-COMMITTEE-ENVI',
        'md5': 'f2e8c30935f956a7165c2f4f4b4ee090',
        'info_dict': {
            'id': '20230524-0900-COMMITTEE-ENVI',
            'ext': 'mp4',
            'release_date': '20230524',
            'title': 'Committee on Environment, Public Health and Food Safety',
            'release_timestamp': 1684912288,
            'live_status': 'was_live',
            'description': 'Committee on Environment, Public Health and Food Safety',
            'duration': 4831,
            'thumbnail': 'https://storage.eup.glcloud.eu/thumbnail/default_thumbnail.png',
            'modified_timestamp': 1732475771,
            'modified_date': '20241124',
        },
    }, {
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/20240320-1345-SPECIAL-PRESSER',
        'md5': '518758eb706471c4c4ef3a134034a5bd',
        'info_dict': {
            'id': '20240320-1345-SPECIAL-PRESSER',
            'ext': 'mp4',
            'release_date': '20240320',
            'title': 'md5:7c6c814cac55dea5e2d87bf8d3db2234',
            'release_timestamp': 1710939767,
            'description': 'md5:7c6c814cac55dea5e2d87bf8d3db2234',
            'duration': 927,
            'thumbnail': 'https://storage.eup.glcloud.eu/thumbnail/default_thumbnail.png',
            'modified_timestamp': 1732475771,
            'modified_date': '20241124',
            'live_status': 'was_live',
        },
    }, {
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/20250328-1600-SPECIAL-PRESSER',
        'md5': 'dd1c5e67eb55e609998583d7c2966105',
        'info_dict': {
            'id': '20250328-1600-SPECIAL-PRESSER',
            'ext': 'mp4',
            'title': 'md5:04a2ab70c183dabe891a7cd190c3121d',
            'description': '',
            'duration': 1023,
            'thumbnail': 'https://storage.eup.glcloud.eu/thumbnail/default_thumbnail.png',
            'release_timestamp': 1743177199,
            'release_date': '20250328',
            'modified_timestamp': 1743180924,
            'modified_date': '20250328',
            'live_status': 'was_live',
        },
    }, {
        'url': 'https://multimedia.europarl.europa.eu/webstreaming/briefing-for-media-on-2024-european-elections_20240429-1000-SPECIAL-OTHER',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lang, video_id = self._match_valid_url(url).group('lang', 'id')
        query = {
            'lang': lang,
            'audio': lang,
            'autoplay': 'true',
            'logo': 'false',
            'muted': 'false',
            'fullscreen': 'true',
            'disclaimer': 'false',
            'multicast': 'true',
            'analytics': 'false',
        }
        webpage = self._download_webpage(f'https://control.eup.glcloud.eu/content-manager/content-page/{video_id}',
                                         video_id, 'Downloading iframe', query=query)
        stream_info = self._search_json(r'<script [^>]*id="ng-state"[^>]*>', webpage, 'stream info', video_id)['contentEventKey']
        player_url = stream_info.get('playerUrl')
        # status = traverse_obj(stream_info, ('media_item', 'mediaSubType'))
        # base = 'https://control.eup.glcloud.eu/content-manager/api/v1/socket.io/?EIO=4&transport=polling'
        # headers = {'referer': f'https://control.eup.glcloud.eu/content-manager/content-page/{video_id}'}
        # sid = self._download_socket_json(base, video_id, note='Opening socket', headers=headers)['sid']
        # base += '&sid=' + sid
        # self._download_webpage(base, video_id, 'Polling socket with payload', data=b'40/content,', headers=headers)
        # self._download_webpage(base, video_id, 'Polling socket', headers=headers)
        # self._download_socket_json(base, video_id, 'Getting broadcast metadata from socket', headers=headers)
        if player_url:
            live_status = 'was_live'
            query = None if stream_info.get('finalVod') else traverse_obj(stream_info, {
                'startTime': ('startTime', {str_or_none}),
                'endTime': ('endTime', {str_or_none}),
            })
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(player_url, video_id, query=query, ext='mp4')
        else:
            formats = None
            subtitles = None
            live_status = 'is_upcoming'
            self.raise_no_formats('Stream didn\'t start yet', True, video_id)
        if stream_info.get('live'):
            live_status = 'is_live'

        return {
            'formats': formats,
            'subtitles': subtitles,
            'live_status': live_status,
            **traverse_obj(stream_info, {
                'id': ('commonId', {str_or_none}),
                'title': ('title', {str_or_none}),
                'description': ('description', {str_or_none}),
                'release_timestamp': ('startTime', {int_or_none}),
                'duration': ('endTime', {lambda e: e and (s := stream_info.get('startTime')) and (e - s)}),
                'thumbnail': ('posterFrame', {url_or_none}),
                'modified_timestamp': ('meta', 'updatedAt', {parse_iso8601}),
            }),
        }
