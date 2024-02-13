from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    parse_age_limit,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class TrueIDIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<domain>vn\.trueid\.net|trueid\.(?:id|ph))/(?:movie|series/[^/]+)/(?P<id>[^/?#&]+)'
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
        'expected_warnings': ['Video is geo restricted.']
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
            'upload_date': '20210112',
            'release_date': '20210131',
        },
        'expected_warnings': ['Video is geo restricted.']
    }, {
        'url': 'https://vn.trueid.net/series/7DNPM7Bpa9wv/pwLgEQ4Xbda2/haikyu-vua-bong-chuyen-phan-1/',
        'info_dict': {
            'id': 'pwLgEQ4Xbda2',
            'ext': 'mp4',
            'title': 'Haikyu!!: Vua Bóng Chuyền Phần 1 - Tập 1',
            'display_id': 'haikyu-vua-bong-chuyen-phan-1-tap-1',
            'description': 'md5:0374dd44d247799169449ee30cca963a',
            'timestamp': 1629270901,
            'categories': ['Anime', 'Phim Hài', 'Phim Học Đường', 'Phim Thể Thao', 'Shounen'],
            'release_timestamp': 1629270720,
            'release_year': 2014,
            'age_limit': 13,
            'thumbnail': 'https://cms.dmpcdn.com/movie/2021/09/28/b6e7ec00-2039-11ec-8436-974544e5841f_webp_original.jpg',
            'upload_date': '20210818',
            'release_date': '20210818',
        },
        'expected_warnings': ['Video is geo restricted.']
    }, {
        'url': 'https://trueid.ph/series/l8rvvAw7Jwv8/l8rvvAw7Jwv8/naruto-trailer/',
        'only_matching': True,
    }]
    _CUSTOM_RATINGS = {
        'PG': 7,
    }

    def _real_extract(self, url):
        domain, video_id = self._match_valid_url(url).group('domain', 'id')
        webpage = self._download_webpage(url, video_id)
        initial_data = traverse_obj(
            self._search_nextjs_data(webpage, video_id, fatal=False), ('props', 'pageProps', 'initialContentData'), default={})

        try:
            stream_data = self._download_json(
                f'https://{domain}/cmsPostProxy/contents/video/{video_id}/streamer?os=android', video_id, data=b'')['data']
        except ExtractorError as e:
            if not isinstance(e.cause, HTTPError):
                raise e
            errmsg = self._parse_json(e.cause.response.read().decode(), video_id)['meta']['message']
            if 'country' in errmsg:
                self.raise_geo_restricted(
                    errmsg, [initial_data['display_country']] if initial_data.get('display_country') else None, True)
            else:
                self.raise_no_formats(errmsg, video_id=video_id)

        if stream_data:
            stream_url = stream_data['stream']['stream_url']
            stream_ext = determine_ext(stream_url)
            if stream_ext == 'm3u8':
                formats, subs = self._extract_m3u8_formats_and_subtitles(stream_url, video_id, 'mp4')
            elif stream_ext == 'mpd':
                formats, subs = self._extract_mpd_formats_and_subtitles(stream_url, video_id)
            else:
                formats = [{'url': stream_url}]

        thumbnails = [
            {'id': thumb_key, 'url': thumb_url}
            for thumb_key, thumb_url in (initial_data.get('thumb_list') or {}).items()
            if url_or_none(thumb_url)]

        return {
            'id': video_id,
            'title': initial_data.get('title') or self._html_search_regex(
                [r'Nonton (?P<name>.+) Gratis',
                 r'Xem (?P<name>.+) Miễn phí',
                 r'Watch (?P<name>.+) Free'], webpage, 'title', group='name'),
            'display_id': initial_data.get('slug_title'),
            'description': initial_data.get('synopsis'),
            'timestamp': unified_timestamp(initial_data.get('create_date')),
            # 'duration': int_or_none(initial_data.get('duration'), invscale=60),  # duration field must atleast be accurate to the second
            'categories': traverse_obj(initial_data, ('article_category_details', ..., 'name')),
            'release_timestamp': unified_timestamp(initial_data.get('publish_date')),
            'release_year': int_or_none(initial_data.get('release_year')),
            'formats': formats,
            'subtitles': subs,
            'thumbnails': thumbnails,
            'age_limit': self._CUSTOM_RATINGS.get(initial_data.get('rate')) or parse_age_limit(initial_data.get('rate')),
            'cast': traverse_obj(initial_data, (('actor', 'director'), ...)),
            'view_count': int_or_none(initial_data.get('count_views')),
            'like_count': int_or_none(initial_data.get('count_likes')),
            'average_rating': int_or_none(initial_data.get('count_ratings')),
        }
