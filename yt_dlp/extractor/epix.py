import json
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    traverse_obj,
)


class EpixBase(InfoExtractor):
    _API_URL = 'https://api.epix.com/v2/'
    _API_KEY = 'f07debfcdf0f442bab197b517a5126ec'
    _HEADERS = {
        'user-agent': 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/65.0.3325.181 Chrome/65.0.3325.181 Safari/537.36',
        'content-type': 'application/json'
    }

    def _real_initialize(self):
        info = self._download_json(f'{self._API_URL}sessions', None, note='Download access token info', headers=self._HEADERS, data=json.dumps({
            'device': {
                'guid': str(uuid.uuid1()),
                'format': 'console',
                'os': 'web',
                'app_version': '1.0.2',
                'model': 'browser',
                'manufacturer': 'google'
            },
            'apikey': self._API_KEY,
            'oauth': {
                'token': None
            }
        }).encode('utf-8'))
        access_token = traverse_obj(info, ('device_session', 'session_token'))
        self._HEADERS.update({
            'x-session-token': access_token
        })


class EpixExtraIE(EpixBase):
    _VALID_URL = r'https?://www\.epix\.com/series/(?P<id>[^(?:/|\?)]+)(?:/extra/\d+|\?|$)'
    IE_NAME = 'epix:extra'
    IE_DESC = 'Epix extra video'
    _TESTS = [{
        'url': 'https://www.epix.com/series/from/extra/13596',
        'md5': 'afedb9351282d7f8aee6e5474d8a7bc8',
        'info_dict': {
            'id': 'from',
            'ext': 'mp4',
            'title': 'FROM Critics Spot (Updated Trailer)',
            'description': 'md5:a8ee8a70b0e4966c56675299a3d70951',
            'thumbnail': r're:^https?://.+\.jpg',
        },
    }, {
        'url': 'https://www.epix.com/series/billy-the-kid',
        'md5': '100e5f60b16d39f1a5d9f1fe302d83ea',
        'info_dict': {
            'id': 'billy-the-kid',
            'ext': 'mp4',
            'title': 'Billy The Kid Trailer',
            'description': 'md5:45b42f96458ee53b765e40d8d8c90998',
            'thumbnail': r're:^https?://.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._download_json(f'{self._API_URL}series/{video_id}', video_id=video_id, headers=self._HEADERS)
        extras_content = traverse_obj(info, ('series', 'extras', 0, 'content'))

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(extras_content.get('hlspath'), video_id=video_id)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': extras_content.get('title'),
            'description': traverse_obj(info, ('series', 'description'), ('series', 'short_description')),
            'subtitles': subtitles,
            'thumbnail': traverse_obj(info, ('series', 'images', 'poster', '16_9', 'xlarge')),
            'formats': formats,
        }


class EpixBaseTraier(EpixBase):

    def _extract_trailer_info(self, info, video_id):
        if not info.get('trailer'):
            raise ExtractorError("Video doesn't have trailer", expected=True)
        formats = [{
            'url': traverse_obj(info, ('trailer', 'url')),
            'ext': 'mp4',
        }]
        fmts, subtitles = self._extract_m3u8_formats_and_subtitles(traverse_obj(info, ('trailer', 'hlspath')), video_id=video_id)
        formats.extend(fmts)
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': info.get('title') or info.get('short_title'),
            'description': traverse_obj(info, 'synopsis', 'short_description'),
            'subtitles': subtitles,
            'thumbnail': traverse_obj(info, ('images', 'poster', '16_9', 'xlarge')),
            'formats': formats,
        }


class EpixTrailerSeasonIE(EpixBaseTraier):
    _VALID_URL = r'https?://www\.epix\.com/series/(?P<id>[^/]+)/season/(?P<season_id>\d+)/episode/(?P<episode_id>\d+)'
    IE_NAME = 'epix:trailer:season'
    IE_DESC = 'Epix trailer season'
    _TESTS = [{
        'url': 'https://www.epix.com/series/from/season/1/episode/3/from-s1-e3?trailer=true',
        'md5': '3f56c06de32ff5453f9a590a12a31d13',
        'info_dict': {
            'id': 'from',
            'ext': 'mp4',
            'title': 'From (S1 E3): Choosing Day',
            'description': 'md5:cb164e038147477cae6a22f400a60f9c',
            'thumbnail': r're:^https?://.+\.jpg',
        },
    }, {
        'url': 'https://www.epix.com/series/britannia/season/1/episode/3/britannia-s1-e3',
        'md5': '1a71cd37b3b380478eae16a34f01ff0b',
        'info_dict': {
            'id': 'britannia',
            'ext': 'mp4',
            'title': 'Britannia (S1 E3): Episode 3',
            'description': 'md5:869360873062204eda1aaa2ddc512cdf',
            'thumbnail': r're:^https?://.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id, season_id, episode_id = self._match_valid_url(url).groups()
        info = self._download_json(f'{self._API_URL}series/{video_id}', video_id=video_id, headers=self._HEADERS)
        if int_or_none(season_id) and int_or_none(episode_id):
            trailer_info = traverse_obj(info, (
                'series', 'items', int_or_none(season_id) - 1, 'content', 'items', int_or_none(episode_id) - 1, 'content'))
        else:
            raise ExtractorError('Extractor failed to obtain "season_id" and "episode_id"', expected=True)
        return self._extract_trailer_info(trailer_info, video_id)


class EpixTrailerMovieIE(EpixBaseTraier):
    _VALID_URL = r'https?://www\.epix\.com/movie\/(?P<id>[^(/|\?)]+)'
    IE_NAME = 'epix:trailer:movie'
    IE_DESC = 'Epix trailer movie'
    _TESTS = [{
        'url': 'https://www.epix.com/movie/the-marksman',
        'md5': '63f2bff2ef775c278dc9095eabc91ab9',
        'info_dict': {
            'id': 'the-marksman',
            'ext': 'mp4',
            'title': 'The Marksman',
            'description': 'md5:4cf53bf15f2e8b0e92e7e0ed1f5f49c5',
            'thumbnail': r're:^https?://.+\.jpg',
        },
    }, {
        # Doesn't have trailer
        'url': 'https://www.epix.com/movie/clifford-the-big-red-dog-2021?play=true',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._download_json(f'{self._API_URL}movies/{video_id}', video_id, headers=self._HEADERS)
        return self._extract_trailer_info(info.get('movie'), video_id)
