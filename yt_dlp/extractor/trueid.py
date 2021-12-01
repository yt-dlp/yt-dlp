# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    parse_age_limit,
    traverse_obj,
    unified_timestamp,
    url_or_none
)


class TrueIDIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?trueid\.id/(?:movie|series/[^/]+)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://trueid.id/movie/XYNlDOZZJzL6/pengabdi-setan/',
        'md5': '2552c7535125885901f1a2a4bcf32ca3',
        'info_dict': {
            'id': 'XYNlDOZZJzL6',
            'ext': 'mp4',
            'title': 'Pengabdi Setan',
            'display_id': 'pengabdi-setan',
            'description': 'md5:b0b41df08601e85e5291496c9bbe52cd',
            'timestamp': 1600243511,
            'categories': ['Film Indonesia', 'Horror', 'Mystery'],
            'release_timestamp': 1593536400,
            'release_year': 1982,
            'cast': list,
            'thumbnail': 'https://cms.dmpcdn.com/movie/2020/09/18/8b6e35c0-f97f-11ea-81fe-c52fc9dd314f_original.png',
            'upload_date': '20200916',
            'release_date': '20200630',
        },
        'params': {
            'format': 'bv'
        }
    }, {
        'url': 'https://trueid.id/series/zZOBVPb62EwR/qXY73rwyl7oj/one-piece-ep-1/',
        'md5': '1c6d976049bc3c89a8a25aed2c3fb081',
        'info_dict': {
            'id': 'qXY73rwyl7oj',
            'ext': 'mp4',
            'title': 'One Piece Ep. 1',
            'display_id': 'one-piece-ep-1',
            'description': 'md5:13226d603bd03c4150a1cf5758e842ea',
            'timestamp': 1610421085,
            'categories': ['Animation & Cartoon', 'Kids & Family', 'Adventure'],
            'release_timestamp': 1612112400,
            'release_year': 1999,
            'age_limit': 7,
            'cast': ['Kounosuke Uda', 'Junji Shimizu'],
            'thumbnail': 'https://cms.dmpcdn.com/movie/2021/01/13/f84e9e70-5562-11eb-9fe2-dd6c2099a468_original.png',
            'duration_string': '23:00',
            'upload_date': '20210112',
            'release_date': '20210131',
        },
        'params': {
            'format': 'bv'
        }
    }]
    _CUSTOM_RATINGS = {
        'PG': 7,
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        initial_data = traverse_obj(
            self._search_nextjs_data(webpage, video_id, fatal=False), ('props', 'pageProps', 'initialContentData'), default={})

        try:
            stream_data = self._download_json(
                f'https://trueid.id/cmsPostProxy/contents/video/{video_id}/streamer?os=android', video_id, data=b'')['data']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError):
                errmsg = self._parse_json(e.cause.read().decode(), video_id)['meta']['message']
                if 'country' in errmsg:
                    self.raise_geo_restricted(
                        errmsg, [initial_data['display_country']] if initial_data.get('display_country') else None, True)
                else:
                    self.raise_no_formats(errmsg, video_id=video_id)
            else:
                raise e

        if stream_data:
            formats, subs = self._extract_m3u8_formats_and_subtitles(stream_data['stream']['stream_url'], video_id, 'mp4')

        thumbnails = []
        for thumb_key in initial_data.get('thumb_list') or {}:
            if url_or_none(initial_data['thumb_list'][thumb_key]):
                thumbnails.append({
                    'id': thumb_key,
                    'url': url_or_none(initial_data['thumb_list'][thumb_key])
                })

        return {
            'id': video_id,
            'title': initial_data.get('title') or self._html_search_regex(
                r'Nonton (?P<name>.+) Gratis \| TrueID', webpage, 'title', group='name'),
            'display_id': initial_data.get('slug_title'),
            'description': initial_data.get('synopsis'),
            'timestamp': unified_timestamp(initial_data.get('create_date')),
            'duration': float_or_none(initial_data.get('duration'), invscale=60),
            'categories': traverse_obj(initial_data, ('article_category_details', ..., 'name')),
            'release_timestamp': unified_timestamp(initial_data.get('publish_date')),
            'release_year': int_or_none(initial_data.get('release_year')),
            'formats': formats,
            'subtitles': subs,
            'thumbnails': thumbnails,
            'age_limit': self._CUSTOM_RATINGS.get(initial_data.get('rate')) or parse_age_limit(initial_data.get('rate')),
            'cast': (initial_data.get('actor') or []) + (initial_data.get('director') or [])
        }
