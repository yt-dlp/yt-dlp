from .common import InfoExtractor
from ..utils import (
    int_or_none,
    orderedSet,
    parse_duration,
    parse_iso8601,
    parse_qs,
    qualities,
    unified_strdate,
    xpath_text
)


class EuropaIE(InfoExtractor):
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
        }
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
            'http://ec.europa.eu/avservices/video/player/playlist.cfm?ID=%s' % video_id, video_id)

        def get_item(type_, preference):
            items = {}
            for item in playlist.findall('./info/%s/item' % type_):
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
                'language_preference': language_preference(lang)
            })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'formats': formats
        }


class EuroParlWebstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:multimedia|webstreaming)\.europarl\.europa\.eu/[^/#?]+/
        (?:embed/embed\.html\?event=|(?!video)[^/#?]+/[\w-]+_)(?P<id>[\w-]+)
    '''
    _TESTS = [{
        'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/plenary-session_20220914-0900-PLENARY',
        'info_dict': {
            'id': 'bcaa1db4-76ef-7e06-8da7-839bd0ad1dbe',
            'ext': 'mp4',
            'release_timestamp': 1663137900,
            'title': 'Plenary session',
            'release_date': '20220914',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/eu-cop27-un-climate-change-conference-in-sharm-el-sheikh-egypt-ep-delegation-meets-with-ngo-represen_20221114-1600-SPECIAL-OTHER',
        'info_dict': {
            'id': 'a8428de8-b9cd-6a2e-11e4-3805d9c9ff5c',
            'ext': 'mp4',
            'release_timestamp': 1668434400,
            'release_date': '20221114',
            'title': 'md5:d3550280c33cc70e0678652e3d52c028',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # embed webpage
        'url': 'https://webstreaming.europarl.europa.eu/ep/embed/embed.html?event=20220914-0900-PLENARY&language=en&autoplay=true&logo=true',
        'info_dict': {
            'id': 'bcaa1db4-76ef-7e06-8da7-839bd0ad1dbe',
            'ext': 'mp4',
            'title': 'Plenary session',
            'release_date': '20220914',
            'release_timestamp': 1663137900,
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # live webstream
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/euroscola_20221115-1000-SPECIAL-EUROSCOLA',
        'info_dict': {
            'ext': 'mp4',
            'id': '510eda7f-ba72-161b-7ee7-0e836cd2e715',
            'release_timestamp': 1668502800,
            'title': 'Euroscola 2022-11-15 19:21',
            'release_date': '20221115',
            'live_status': 'is_live',
        },
        'skip': 'not live anymore'
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        json_info = self._download_json(
            'https://vis-api.vuplay.co.uk/event/external', display_id,
            query={
                'player_key': 'europarl|718f822c-a48c-4841-9947-c9cb9bb1743c',
                'external_id': display_id,
            })

        formats, subtitles = self._extract_mpd_formats_and_subtitles(json_info['streaming_url'], display_id)
        fmts, subs = self._extract_m3u8_formats_and_subtitles(
            json_info['streaming_url'].replace('.mpd', '.m3u8'), display_id)

        formats.extend(fmts)
        self._merge_subtitles(subs, target=subtitles)

        return {
            'id': json_info['id'],
            'title': json_info.get('title'),
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': parse_iso8601(json_info.get('published_start')),
            'is_live': 'LIVE' in json_info.get('state', '')
        }
