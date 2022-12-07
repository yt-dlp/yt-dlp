from .common import InfoExtractor
from ..utils import int_or_none, parse_iso8601, traverse_obj


class IVXPlayerIE(InfoExtractor):
    _VALID_URL = r'ivxplayer:(?P<video_id>\d+):(?P<player_key>\w+)'
    _TESTS = [{
        'url': 'ivxplayer:2366065:4a89dfe6bc8f002596b1dfbd600730b1',
        'info_dict': {
            'id': '2366065',
            'ext': 'mp4',
            'duration': 112,
            'upload_date': '20221204',
            'title': 'Film Indonesia di Disney Content Showcase Asia Pacific 2022',
            'timestamp': 1670151746,
        }
    }]

    def _extract_from_webpage(self, url, webpage):
        player_key, video_id = self._search_regex(
            r'<ivs-player\s*[^>]+data-ivs-key\s*=\s*"(?P<player_key>[\w]+)\s*[^>]+\bdata-ivs-vid="(?P<video_id>[\w-]+)',
            webpage, 'player_key, video_id', group=('player_key', 'video_id'), default=(None, ''))
        if not player_key:
            return
        print(f'ivxplayer:{video_id}:{player_key}')
        yield self.url_result(f'ivxplayer:{video_id}:{player_key}', IVXPlayerIE, url_transparent=True)

    # TODO: set change tempo.py to use this extractor
    # TODO: only use video_id and player key
    def _real_extract(self, url):
        video_id, player_key = self._match_valid_url(url).group('video_id', 'player_key')
        json_data = self._download_json(
            f'https://ivxplayer.ivideosmart.com/prod/video/{video_id}?key={player_key}', video_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            json_data['player']['video_url'], video_id)

        return {
            'id': str(json_data['ivx']['id']),
            'title': traverse_obj(json_data, ('ivx', 'name')),
            'description': traverse_obj(json_data, ('ivx', 'description')),
            'duration': int_or_none(traverse_obj(json_data, ('ivx', 'duration'))),
            'timestamp': parse_iso8601(traverse_obj(json_data, ('ivx', 'published_at'))),
            'formats': formats,
            'subtitles': subtitles,
        }


class IVXPlayerEmbedIE(InfoExtractor):
    _VALID_URL = False
    _WEBPAGE_TESTS = [{
        'url': 'https://www.cantika.com/video/31737/film-indonesia-di-disney-content-showcase-asia-pacific-2022',
        'info_dict': {
            'id': 'fixme',
            'ext': 'mp4',
        },
        'params': {
            'allowed_extractors': ['ivxplayer.*']
        }
    }, {
        'url': 'https://www.gooto.com/video/11437/wuling-suv-ramai-dikunjungi-di-giias-2018',
        'info_dict': {
            'id': 'fixme',
            'ext': 'mp4',
        }
    }]

    def _extract_from_webpage(self, url, webpage):
        player_key, video_id = self._search_regex(
            r'<ivs-player\s*[^>]+data-ivs-key\s*=\s*"(?P<player_key>[\w]+)\s*[^>]+\bdata-ivs-vid="(?P<video_id>[\w-]+)',
            webpage, 'player_key, video_id', group=('player_key', 'video_id'), default=(None, ''))
        if not player_key:
            return
        print(f'ivxplayer:{video_id}:{player_key}')
        yield self.url_result(f'ivxplayer:{video_id}:{player_key}', IVXPlayerIE, url_transparent=True)
