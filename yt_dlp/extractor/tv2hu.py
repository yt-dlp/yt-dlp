# encoding: utf-8
from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    UnsupportedError,
)


class TV2HuIE(InfoExtractor):
    IE_NAME = 'tv2play.hu'
    _VALID_URL = r'https?://(?:www\.)?tv2play\.hu/(?!szalag/)(?P<id>[^#&?]+)'
    _TESTS = [{
        'url': 'https://tv2play.hu/mintaapak/mintaapak_213_epizod_resz',
        'info_dict': {
            'id': '249240',
            'ext': 'mp4',
            'title': 'Mintaapák - 213. epizód',
            'series': 'Mintaapák',
            'duration': 2164,
            'description': 'md5:7350147e75485a59598e806c47967b07',
            'thumbnail': r're:^https?://.*\.jpg$',
            'release_date': '20210825',
            'season_number': None,
            'episode_number': 213,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://tv2play.hu/taxi_2',
        'md5': '585e58e2e090f34603804bb2c48e98d8',
        'info_dict': {
            'id': '199363',
            'ext': 'mp4',
            'title': 'Taxi 2',
            'series': 'Taxi 2',
            'duration': 5087,
            'description': 'md5:47762155dc9a50241797ded101b1b08c',
            'thumbnail': r're:^https?://.*\.jpg$',
            'release_date': '20210118',
            'season_number': None,
            'episode_number': None,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        json_data = self._download_json(f'https://tv2play.hu/api/search/{id}', id)

        if json_data['contentType'] == 'showpage':
            ribbon_ids = traverse_obj(json_data, ('pages', ..., 'tabs', ..., 'ribbonIds'), get_all=False, expected_type=list)
            entries = [self.url_result(f'https://tv2play.hu/szalag/{ribbon_id}',
                                       ie=TV2HuSeriesIE.ie_key(), video_id=ribbon_id) for ribbon_id in ribbon_ids]
            return self.playlist_result(entries, playlist_id=id)
        elif json_data['contentType'] != 'video':
            raise UnsupportedError(url)

        video_id = str(json_data['id'])
        player_id = json_data.get('playerId')
        series_json = json_data.get('seriesInfo', {})

        video_json_url = self._download_json(f'https://tv2play.hu/api/streaming-url?playerId={player_id}', video_id)['url']
        video_json = self._download_json(video_json_url, video_id)
        m3u8_url = self._proto_relative_url(traverse_obj(video_json, ('bitrates', 'hls')))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id)

        return {
            'id': video_id,
            'title': json_data['title'],
            'series': json_data.get('seriesTitle'),
            'duration': json_data.get('length'),
            'description': json_data.get('description'),
            'thumbnail': 'https://tv2play.hu' + json_data.get('thumbnailUrl'),
            'release_date': json_data.get('uploadedAt').replace('.', ''),
            'season_number': series_json.get('seasonNr'),
            'episode_number': series_json.get('episodeNr'),
            'formats': formats,
            'subtitles': subtitles,
        }


class TV2HuSeriesIE(InfoExtractor):
    IE_NAME = 'tv2playseries.hu'
    _VALID_URL = r'https?://(?:www\.)?tv2play\.hu/szalag/(?P<id>[^#&?]+)'

    _TESTS = [{
        'url': 'https://tv2play.hu/szalag/59?rendezes=nepszeruseg',
        'playlist_mincount': 284,
        'info_dict': {
            'id': '59',
        }
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        json_data = self._download_json(f'https://tv2play.hu/api/ribbons/{id}/0?size=100000', id)
        entries = []
        for card in json_data.get('cards', []):
            video_id = card.get('slug')
            if video_id:
                entries.append(self.url_result(f'https://tv2play.hu/{video_id}',
                                               ie=TV2HuIE.ie_key(), video_id=video_id))

        return self.playlist_result(entries, playlist_id=id)
