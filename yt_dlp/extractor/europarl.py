from .common import InfoExtractor
from ..utils import parse_iso8601


class EuroParlWebstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://
                        (
                            (multimedia|webstreaming)
                            \.europarl\.europa\.eu/[^/]+
                            /(embed/embed\.html\?\bevent=|(?!video)([^/]+)/[\w-]+_)
                        )
                        (?P<id>[\w-]+)
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
