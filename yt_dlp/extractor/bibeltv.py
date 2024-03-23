import functools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    format_field,
    int_or_none,
    js_to_json,
    orderedSet,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class BibelTVBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['AT', 'CH', 'DE']
    _GEO_BYPASS = False

    API_URL = 'https://www.bibeltv.de/mediathek/api'
    AUTH_TOKEN = 'j88bRXY8DsEqJ9xmTdWhrByVi5Hm'

    def _extract_formats_and_subtitles(self, data, crn_id, *, is_live=False):
        formats = []
        subtitles = {}
        for media_url in traverse_obj(data, (..., 'src', {url_or_none})):
            media_ext = determine_ext(media_url)
            if media_ext == 'm3u8':
                m3u8_formats, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    media_url, crn_id, live=is_live)
                formats.extend(m3u8_formats)
                subtitles.update(m3u8_subs)
            elif media_ext == 'mpd':
                mpd_formats, mpd_subs = self._extract_mpd_formats_and_subtitles(media_url, crn_id)
                formats.extend(mpd_formats)
                subtitles.update(mpd_subs)
            elif media_ext == 'mp4':
                formats.append({'url': media_url})
            else:
                self.report_warning(f'Unknown format {media_ext!r}')

        return formats, subtitles

    @staticmethod
    def _extract_base_info(data):
        return {
            'id': data['crn'],
            **traverse_obj(data, {
                'title': 'title',
                'description': 'description',
                'duration': ('duration', {functools.partial(int_or_none, scale=1000)}),
                'timestamp': ('schedulingStart', {parse_iso8601}),
                'season_number': 'seasonNumber',
                'episode_number': 'episodeNumber',
                'view_count': 'viewCount',
                'like_count': 'likeCount',
            }),
            'thumbnails': orderedSet(traverse_obj(data, ('images', ..., {
                'url': ('url', {url_or_none}),
            }))),
        }

    def _extract_url_info(self, data):
        return {
            '_type': 'url',
            'url': format_field(data, 'slug', 'https://www.bibeltv.de/mediathek/videos/%s'),
            **self._extract_base_info(data),
        }

    def _extract_video_info(self, data):
        crn_id = data['crn']

        if data.get('drm'):
            self.report_drm(crn_id)

        json_data = self._download_json(
            format_field(data, 'id', f'{self.API_URL}/video/%s'), crn_id,
            headers={'Authorization': self.AUTH_TOKEN}, fatal=False,
            errnote='No formats available') or {}

        formats, subtitles = self._extract_formats_and_subtitles(
            traverse_obj(json_data, ('video', 'videoUrls', ...)), crn_id)

        return {
            '_type': 'video',
            **self._extract_base_info(data),
            'formats': formats,
            'subtitles': subtitles,
        }


class BibelTVVideoIE(BibelTVBaseIE):
    IE_DESC = 'BibelTV single video'
    _VALID_URL = r'https?://(?:www\.)?bibeltv\.de/mediathek/videos/(?P<id>\d+)[\w-]+'
    IE_NAME = 'bibeltv:video'

    _TESTS = [{
        'url': 'https://www.bibeltv.de/mediathek/videos/344436-alte-wege',
        'md5': 'ec1c07efe54353780512e8a4103b612e',
        'info_dict': {
            'id': '344436',
            'ext': 'mp4',
            'title': 'Alte Wege',
            'description': 'md5:2f4eb7294c9797a47b8fd13cccca22e9',
            'timestamp': 1677877071,
            'duration': 150.0,
            'upload_date': '20230303',
            'thumbnail': r're:https://bibeltv\.imgix\.net/[\w-]+\.jpg',
            'episode': 'Episode 1',
            'episode_number': 1,
            'view_count': int,
            'like_count': int,
        },
        'params': {
            'format': '6',
        },
    }]

    def _real_extract(self, url):
        crn_id = self._match_id(url)
        video_data = traverse_obj(
            self._search_nextjs_data(self._download_webpage(url, crn_id), crn_id),
            ('props', 'pageProps', 'videoPageData', 'videos', 0, {dict}))
        if not video_data:
            raise ExtractorError('Missing video data.')

        return self._extract_video_info(video_data)


class BibelTVSeriesIE(BibelTVBaseIE):
    IE_DESC = 'BibelTV series playlist'
    _VALID_URL = r'https?://(?:www\.)?bibeltv\.de/mediathek/serien/(?P<id>\d+)[\w-]+'
    IE_NAME = 'bibeltv:series'

    _TESTS = [{
        'url': 'https://www.bibeltv.de/mediathek/serien/333485-ein-wunder-fuer-jeden-tag',
        'playlist_mincount': 400,
        'info_dict': {
            'id': '333485',
            'title': 'Ein Wunder für jeden Tag',
            'description': 'Tägliche Kurzandacht mit Déborah Rosenkranz.',
        },
    }]

    def _real_extract(self, url):
        crn_id = self._match_id(url)
        webpage = self._download_webpage(url, crn_id)
        nextjs_data = self._search_nextjs_data(webpage, crn_id)
        series_data = traverse_obj(nextjs_data, ('props', 'pageProps', 'seriePageData', {dict}))
        if not series_data:
            raise ExtractorError('Missing series data.')

        return self.playlist_result(
            traverse_obj(series_data, ('videos', ..., {dict}, {self._extract_url_info})),
            crn_id, series_data.get('title'), clean_html(series_data.get('description')))


class BibelTVLiveIE(BibelTVBaseIE):
    IE_DESC = 'BibelTV live program'
    _VALID_URL = r'https?://(?:www\.)?bibeltv\.de/livestreams/(?P<id>[\w-]+)'
    IE_NAME = 'bibeltv:live'

    _TESTS = [{
        'url': 'https://www.bibeltv.de/livestreams/bibeltv/',
        'info_dict': {
            'id': 'bibeltv',
            'ext': 'mp4',
            'title': 're:Bibel TV',
            'live_status': 'is_live',
            'thumbnail': 'https://streampreview.bibeltv.de/bibeltv.webp',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.bibeltv.de/livestreams/impuls/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        stream_id = self._match_id(url)
        webpage = self._download_webpage(url, stream_id)
        stream_data = self._search_json(
            r'\\"video\\":', webpage, 'bibeltvData', stream_id,
            transform_source=lambda jstring: js_to_json(jstring.replace('\\"', '"')))

        formats, subtitles = self._extract_formats_and_subtitles(
            traverse_obj(stream_data, ('src', ...)), stream_id, is_live=True)

        return {
            'id': stream_id,
            'title': stream_data.get('title'),
            'thumbnail': stream_data.get('poster'),
            'is_live': True,
            'formats': formats,
            'subtitles': subtitles,
        }
