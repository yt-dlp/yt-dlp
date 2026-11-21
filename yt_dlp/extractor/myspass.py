from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    str_or_none,
    traverse_obj,
    unified_timestamp,
    urljoin,
)


class MySpassIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?myspass\.de/(?:[^/]+/)*\d+-\d+-(?P<id>\d+)/?$'
    _BASE_CDN_URL = 'https://1754936693.rsc.cdn77.org'
    _BASE_API_URL = 'https://cms-myspass.vanilla-ott.com/api'
    _API_TOKEN = '62ff4a5639cf19050b28398e5555659835fdd6dce188dad0484d876fedffcd80a4f54b53892299f298e94021c249383469d6ffcc9fa9f4762dacfcaf804f775cd1dec714b6c4db67e60238f14b9d2fc2184a0b171f4d7f43edf08254ca7f810213bccc37c9f26d1c6934892bb1f1169b5ac295ca3c26aaaaea751dd28be6c9a9'

    _TESTS = [{
        'url': 'https://www.myspass.de/folge/tv-total/2022/novak-puffovic-bei-bester-laune/1-72-4007',
        'md5': 'eb8474e5a4b159ce075d9df74cd4f246',
        'info_dict': {
            'id': '4007',
            'ext': 'mp4',
            'title': 'Novak Puffovic bei bester Laune',
            'description': 'md5:74c7f886e00834417f1e427ab0da6121',
            'thumbnail': r're:.*\.jpg',
            'timestamp': 1641945600,
            'upload_date': '20220112',
            'duration': 2941.0,
            'tags': 'count:54',
            'series': 'TV total',
            'series_id': '1',
            'season': '2022',
            'season_number': 2,
            'season_id': '72',
            'episode': 'TV total Sendung vom 12.01.2022',
            'episode_number': 8,
            'episode_id': '505',
        },
    }]

    _PAGE_SIZE = 100

    def _parse_video(self, json):
        video_id = traverse_obj(json, ('id', {str_or_none}))
        video_url = traverse_obj(json, ('attributes', 'video_url', {urljoin(self._BASE_CDN_URL)}))

        formats, subtitles = [], {}
        if video_url.endswith('m3u8'):  # older videos are served as .mp4
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id, ext='mp4', fatal=False)
            for fmt in formats:  # sometimes formats are missing
                fmt['__needs_testing'] = True
        else:
            formats.append({'url': video_url})
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,

            **traverse_obj(json['attributes'], {
                'title': ('title', {str}),
                'description': ('teaser_text', {str}),
                'thumbnail': ('thumbnail_url', {urljoin(self._BASE_CDN_URL)}),
                'timestamp': ('broadcast_date', {unified_timestamp}),
                'duration': ('play_length', {int}),
                'tags': ('keywords', {lambda x: x.split(',')}),
                'series': ('format', 'data', 'attributes', 'name', {str}),
                'series_id': ('format', 'data', 'id', {str_or_none}),
                'season': ('season', 'data', 'attributes', 'name', {str}),
                'season_number': ('season', 'data', 'attributes', 'number', {int}),
                'season_id': ('season', 'data', 'id', {str_or_none}),
                'episode': ('episode', 'data', 'attributes', 'title', {str}),
                'episode_number': ('episode', 'data', 'attributes', 'number', {int}),
                'episode_id': ('episode', 'data', 'id', {str_or_none}),
            }),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        json = self._download_json(
            f'{self._BASE_API_URL}/videos/{video_id}', video_id, 'API request', query={
                'populate': 'format,season,episode',
            }, headers={
                'Authorization': f'Bearer {self._API_TOKEN}',
            })

        return self._parse_video(json['data'])


class MySpassPlayer(MySpassIE):
    _VALID_URL = r'https?://(?:www\.)?myspass\.de/player/(?:[^/]+/)*(?P<id>\d+)/?$'

    _TESTS = [{
        'url': 'https://www.myspass.de/player/staffel-5/pussyterror-tv-sendung-vom-30052019/5946',
        'md5': '1fe100136640abb14c205f091a13ca21',
        'info_dict': {
            'id': '5946',
            'ext': 'mp4',
            'title': 'PussyTerror TV - Sendung vom 30.05.2019',
            'description': 'md5:abb633cb1a2e2f2b752fc8ab0802961c',
            'thumbnail': r're:.*\.jpg',
            'timestamp': 1559174400,
            'upload_date': '20190530',
            'duration': 2584.0,
            'tags': 'count:95',
            'series': 'PussyTerror TV',
            'series_id': '48',
            'season': 'Staffel 5',
            'season_number': 5,
            'season_id': '161',
        },
    }]


class MySpassSeasonIE(MySpassIE):
    _VALID_URL = r'https?://(?:www\.)?myspass\.de/(?:[^/]+/)*(?P<series_id>\d+)-(?P<season_id>\d+)/?$'

    _TESTS = [{
        'url': 'https://www.myspass.de/staffel/comedy-allstars-meilensteine-des-humors/comedy-allstars-2025/30-184',
        'info_dict': {
            'id': '184',
            'title': 'Comedy Allstars | 2025',
            'description': 'md5:3a6a91e8e8b94ab090acf6557c0fe66c',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://www.myspass.de/staffel/tv-total/2022/1-72',
        'info_dict': {
            'id': '72',
            'title': '2022',
            'description': 'md5:41b5eea275eb8a2f3d78a85c6dec98ca',
        },
        'playlist_count': 42,
    }, {
        'url': 'https://www.myspass.de/staffel/die-1live-koeln-comedynacht-xxl/2019/27-91',
        'info_dict': {
            'id': '91',
            'title': '2019',
            'description': 'md5:ddcda36101025a6472fbf56f287441ae',
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        series_id, season_id = self._match_valid_url(url).group('series_id', 'season_id')

        def fetch_page(page_num):
            page_num += 1
            json = self._download_json(
                f'{self._BASE_API_URL}/videos', season_id, f'Downloading season playlist JSON, page {page_num}', query={
                    'filters[format][id][$eq]': series_id,
                    'filters[season][id][$eq]': season_id,
                    'populate': 'format,season,episode',
                    'sort[0]': 'episode.number:asc',
                    'sort[1]': 'special_number:asc',
                    'pagination[pageSize]': self._PAGE_SIZE,
                    'pagination[page]': page_num,
                }, headers={
                    'Authorization': f'Bearer {self._API_TOKEN}',
                })

            for item in json['data']:
                yield self._parse_video(item)

        season_data = self._download_json(
            f'{self._BASE_API_URL}/seasons/{season_id}', season_id, 'Downloading season JSON', headers={
                'Authorization': f'Bearer {self._API_TOKEN}',
            })

        title = traverse_obj(season_data, ('data', 'attributes', 'name'))
        description = traverse_obj(season_data, ('data', 'attributes', 'long_description'))

        entries = OnDemandPagedList(fetch_page, self._PAGE_SIZE)
        return self.playlist_result(entries, season_id, title, description)


class MySpassSeriesIE(MySpassIE):
    _VALID_URL = r'https?://(?:www\.)?myspass\.de/(?:[^/]+/)*(?P<series_id>\d+)/?$'

    _TESTS = [{
        'url': 'https://www.myspass.de/format/mircomania/35',
        'info_dict': {
            'id': '35',
            'title': 'Mircomania',
            'description': 'md5:85a9fd8936887cdad9f7d4d3504e9b3a',
        },
        'playlist_count': 13,
    }, {
        'url': 'https://www.myspass.de/format/die-wochenshow/222',
        'info_dict': {
            'id': '222',
            'title': 'Die Wochenshow',
            'description': 'md5:337158ae37c42fcff352731d8bd1e815',
        },
        'playlist_count': 177,
    }]

    def _real_extract(self, url):
        series_id = self._match_valid_url(url).group('series_id')

        def fetch_page(page_num):
            page_num += 1
            json = self._download_json(
                f'{self._BASE_API_URL}/videos', series_id, f'Downloading series playlist JSON, page {page_num}', query={
                    'filters[format][id][$eq]': series_id,
                    'sort[segment_number]': 'asc',
                    'populate': 'format,season,episode',
                    'sort[episode][number]': 'asc',
                    'pagination[pageSize]': self._PAGE_SIZE,
                    'pagination[page]': page_num,
                }, headers={
                    'Authorization': f'Bearer {self._API_TOKEN}',
                })

            for item in json['data']:
                yield self._parse_video(item)

        series_data = self._download_json(
            f'{self._BASE_API_URL}/formats/{series_id}', series_id, 'Downloading series JSON', headers={
                'Authorization': f'Bearer {self._API_TOKEN}',
            })

        title = traverse_obj(series_data, ('data', 'attributes', 'name'))
        description = traverse_obj(series_data, ('data', 'attributes', 'long_description'))

        entries = OnDemandPagedList(fetch_page, self._PAGE_SIZE)
        return self.playlist_result(entries, series_id, title, description)
