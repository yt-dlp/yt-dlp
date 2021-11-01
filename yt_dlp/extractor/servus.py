# coding: utf-8
from __future__ import unicode_literals

import json
from operator import itemgetter

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_urlparse,
    compat_parse_qs,
)
from ..utils import (
    get_element_by_id,
    parse_iso8601,
    traverse_obj,
    ExtractorError,
    OnDemandPagedList,
)


class ServusTVIE(InfoExtractor):
    IE_NAME = 'servustv'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?servustv.com
                        /[\w-]+/(?:v|[bp]/[\w-]+)
                        /(?P<id>[A-Za-z0-9-]+)
                    '''
    _GEO_COUNTRIES = ['AT', 'DE', 'CH', 'LI', 'IT']
    _API_URL = 'https://api-player.redbull.com/stv/servus-tv'
    _QUERY_API_URL = 'https://backend.servustv.com/wp-json/rbmh/v2/query-filters/query/'
    _LIVE_URLS = {
        'AT': 'https://dms.redbull.tv/v4/destination/stv/stv-linear'
              '/personal_computer/chrome/at/de_AT/playlist.m3u8',
        'DE': 'https://dms.redbull.tv/v4/destination/stv/stv-linear'
              '/personal_computer/chrome/de/de_DE/playlist.m3u8',
    }

    _TESTS = [{
        # new URL schema
        'url': 'https://www.servustv.com/volkskultur/v/aa-28jq9b51h1w11/',
        'info_dict': {
            'id': 'aa-28jq9b51h1w11',
            'ext': 'mp4',
            'title': 'Der Hof meines Vertrauens',
            'description': 'Rinder, Gemüse, Schnecken - drei Selbstvermarkter zeigen ihren Hof.',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1635538304,
            'upload_date': '20211029',
        },
        'params': {'skip_download': True, 'format': 'bestvideo', 'geo_bypass': False},
    }, {
        # playlist
        'url': 'https://www.servustv.com/volkskultur/b/ich-bauer/aa-1qcy94h3s1w11/',
        'info_dict': {
            'id': '116155',
            'title': 'Ich, Bauer',
            'description': 'md5:04cd98226e5c07ca50d0dc90f4a27ea1',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://www.servustv.com/allgemein/v/aagevnv3syv5kuu8cpfq/',
        'only_matching': True,
    }, {
        'url': 'https://www.servustv.com/allgemein/p/jetzt-live/119753/',
        'only_matching': True,
    }]

    def __init__(self, downloader=None):
        super().__init__(downloader=downloader)
        self.country_code = 'AT'
        self.timezone = 'Europe/Vienna'

    def _entry_by_id(self, video_id, video_url=None, is_live=False):
        info = self._download_json(
            self._API_URL, query={'videoId': video_id.upper(), 'timeZone': self.timezone},
            video_id=video_id, fatal=False, expected_status=(400, 404, 500)) \
            or {'message': 'Bad JSON Response'}

        if 'message' in info:
            raise ExtractorError(info['message'], video_id=video_id, expected=True)

        info.setdefault('videoUrl', video_url)
        errors = ", ".join(info.get('playabilityErrors', ()))
        if errors and info.get('videoUrl') is None:
            raise ExtractorError(
                f'{info.get("title", "Unknown")} - {errors}', video_id=video_id, expected=True)

        try:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                info['videoUrl'], video_id=video_id,
                entry_protocol='m3u8' if is_live else 'm3u8_native',
                errnote='Stream not available')
        except ExtractorError as exc:
            raise ExtractorError(exc.msg, video_id=video_id, expected=True)

        self._sort_formats(formats)
        for fmt in formats:
            if 'height' in fmt:
                fmt['format_id'] = f"{fmt['height']}p"

        return {
            'id': video_id,
            'title': info.get('title'),
            'description': info.get('description'),
            'thumbnail': info.get('poster'),
            'duration': None if is_live else info.get('duration'),
            'timestamp': parse_iso8601(info.get('currentSunrise')),
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _live_stream_from_schedule(self, schedule):
        live_url = self._LIVE_URLS['AT']
        for item in sorted(schedule, key=lambda x: x.get('is_live', False), reverse=True):
            is_live = item.get('is_live', False)
            video_url = self._LIVE_URLS.get(self.country_code, live_url) if is_live else None
            return self._entry_by_id(item['aa_id'].lower(), video_url=video_url, is_live=is_live)

    def _paged_playlist_entries(self, query_id, query_type, page_size=20):
        query = {query_type: query_id}
        query.update(dict(
            geo_override=self.country_code, post_type='media_asset', per_page=page_size,
            filter_playability='true', order='desc', orderby='rbmh_playability'))

        def fetch_page(page_number):
            query.update({'page': page_number + 1})
            info = self._download_json(
                self._QUERY_API_URL,
                query=query,
                video_id=f'{query_type}-{query_id}',
                note=f"Downloading entries "
                     f"{page_number * page_size + 1}-{(page_number + 1) * page_size}")

            for item in info['posts']:
                if not traverse_obj(item, ('stv_duration', 'raw')):
                    continue
                video_id, title, url = itemgetter('slug', 'stv_short_title', 'link')(item)
                yield self.url_result(
                    url,
                    ie=self.ie_key(),
                    video_id=video_id,
                    video_title=title
                )

        return OnDemandPagedList(fetch_page, page_size)

    @staticmethod
    def _page_id(json_obj):
        for key, value in traverse_obj(json_obj, ('source', 'data'), default={}).items():
            if isinstance(value, dict) and 'id' in value:
                return value['id']
        return None

    @staticmethod
    def _json_extract(webpage, video_id):
        json_string = get_element_by_id('__FRONTITY_CONNECT_STATE__', webpage)
        if not json_string:
            raise ExtractorError('Missing HTML metadata', video_id=video_id, expected=True)

        try:
            return json.loads(json_string or '{}')
        except json.JSONDecodeError:
            raise ExtractorError('Bad JSON metadata', video_id=video_id, expected=False)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        parsed_url = compat_urllib_parse_urlparse(url)
        url_query = {
            key.lower(): value[0] for key, value in compat_parse_qs(parsed_url.query).items()}

        geo_bypass_country = self.get_param('geo_bypass_country')
        if geo_bypass_country:
            self.country_code = geo_bypass_country.upper()
            self.to_screen(f'Set countrycode to {self.country_code!r}')

        # server accepts tz database names
        # see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        if 'timezone' in url_query:
            self.timezone = url_query['timezone']
            self.to_screen(f'Set timezone to {self.timezone!r}')

        # single video
        if '/v/' in parsed_url.path:
            return self._entry_by_id(video_id)

        webpage = self._download_webpage(url, video_id=video_id)
        json_obj = self._json_extract(webpage, video_id=video_id)

        # find livestreams
        live_schedule = traverse_obj(
            json_obj, ('source', 'page', video_id, 'stv_live_player_schedule'), default=None)
        if live_schedule:
            return self._live_stream_from_schedule(live_schedule)

        # create playlist
        page_id = self._page_id(json_obj)
        if page_id is None:
            raise ExtractorError('Missing page id', video_id=video_id)

        asset_paths = (
            ('source', 'media_asset', str(page_id), 'categories'),
            # ('source', 'page', str(page_id), 'asset_content_color'),
        )

        for *path, asset_name in asset_paths:
            asset_ids = traverse_obj(json_obj, (*path, asset_name), default=())
            if asset_ids:
                query_id, query_type = asset_ids[0], asset_name
                break
        else:
            raise ExtractorError('Website contains no supported playlists',
                                 video_id=page_id, expected=True)

        site_name = self._og_search_property('site_name', webpage, default=None)
        playlist_title = self._og_search_title(webpage, default=None)
        if site_name and playlist_title:
            playlist_title = playlist_title.replace(f' - {site_name}', '', 1)
        playlist_description = self._og_search_description(webpage, default=None)

        return self.playlist_result(
            self._paged_playlist_entries(query_id=query_id, query_type=query_type),
            playlist_id=str(page_id),
            playlist_title=playlist_title,
            playlist_description=playlist_description
        )


class PmWissenIE(ServusTVIE):
    IE_NAME = 'pm-wissen'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?pm-wissen.com
                        /videos
                        /(?P<id>[aA]{2}-\w+)
                    '''

    _TESTS = [{
        'url': 'https://www.pm-wissen.com/videos/aa-24mus4g2w2112/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._entry_by_id(video_id)
