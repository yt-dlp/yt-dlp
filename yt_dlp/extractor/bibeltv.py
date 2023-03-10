from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    LazyList,
    clean_html,
    determine_ext,
    js_to_json,
    parse_iso8601,
    try_get
)


class BibelTVIE(InfoExtractor):
    IE_DESC = 'BibelTV'
    _VALID_URL = r'https?://(?:www\.)?bibeltv\.de/mediathek/videos/(?:crn/)?(?P<id>\d+)'
    _RETURN_TYPE = 'video'

    _GEO_COUNTRIES = ['AT', 'CH', 'DE']
    _GEO_BYPASS = False

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
            'upload_date': '20230303',
            'view_count': int,
            'episode': 'Episode 1',
            'thumbnail': r're:https://bibeltv\.imgix\.net/[\w-]+\.jpg',
            'like_count': int,
            'episode_number': 1,
            'duration': 150.0,
        },
        'params': {
            'format': '6',
        },
    }, {
        'url': 'https://www.bibeltv.de/mediathek/videos/crn/326374',
        'only_matching': True,
    }]
    API_URL = 'https://www.bibeltv.de/mediathek/api'
    AUTH_TOKEN = 'j88bRXY8DsEqJ9xmTdWhrByVi5Hm'

    def _extract_formats_and_subtitles(self, data, crn_id, *, is_live=False):
        formats = []
        subtitles = {}
        for media in data:
            media_url = media['src']
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
                formats.append({'url': media['src']})
            else:
                self.report_warning(f'Unknown format {media_ext!r}')

        return formats, subtitles

    @staticmethod
    def _extract_url_info(data):
        crn_id = data['crn']

        return {
            '_type': 'url',
            'id': crn_id,
            'url': format_field(data, 'slug', 'https://www.bibeltv.de/mediathek/videos/%s'),
            'title': data.get('title'),
            'description': data.get('description'),
            'duration': try_get(data, lambda x: x['duration'] / 1000),
            'timestamp': parse_iso8601(data.get('schedulingStart')),
            'thumbnails': [{'url': url} for url in {image['url'] for image in data.get('images', ())}],
            'season_number': data.get('seasonNumber'),
            'episode_number': data.get('episodeNumber'),
        }

    def _extract_video(self, data):
        video_id = data['id']
        crn_id = data['crn']

        json_data = self._download_json(
            f'{self.API_URL}/video/{video_id}', crn_id, headers={'Authorization': self.AUTH_TOKEN}
        )
        if json_data.get('status') != 'success':
            raise ExtractorError('Failed to load JSON metadata')

        formats, subtitles = self._extract_formats_and_subtitles(
            try_get(json_data, lambda x: x['video']['videoUrls'], list) or [], crn_id)

        return {
            'id': crn_id,
            'title': data.get('title'),
            'description': data.get('description'),
            'duration': try_get(data, lambda x: x['duration'] / 1000),
            'timestamp': parse_iso8601(data.get('schedulingStart')),
            'thumbnails': [{'url': url} for url in {image['url'] for image in data.get('images', ())}],
            'formats': formats,
            'subtitles': subtitles,
            'season_number': data.get('seasonNumber'),
            'episode_number': data.get('episodeNumber'),
            'view_count': data.get('viewCount'),
            'like_count': data.get('likeCount'),
        }

    def _real_extract(self, url):
        crn_id = self._match_id(url)
        webpage = self._download_webpage(url, crn_id)
        nextjs_data = self._search_nextjs_data(webpage, crn_id)
        video_data = try_get(nextjs_data,
                             lambda x: x['props']['pageProps']['videoPageData']['videos'][0], dict)
        if not video_data:
            raise ExtractorError('Missing video data.')

        return self._extract_video(video_data)


class BibelTvSerienIE(BibelTVIE):
    IE_DESC = 'BibelTV'
    _VALID_URL = r'https?://(?:www\.)?bibeltv\.de/mediathek/serien/(?:crn/)?(?P<id>\d+)'
    _RETURN_TYPE = 'playlist'

    IE_NAME = 'bibeltv:serien'

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
        serie_data = try_get(nextjs_data,
                             lambda x: x['props']['pageProps']['seriePageData'], dict)
        if not serie_data:
            raise ExtractorError('Missing series data.')

        video_data = serie_data.get('videos', ())

        return self.playlist_result(
            LazyList(map(self._extract_url_info, video_data)),
            playlist_id=crn_id,
            playlist_title=serie_data.get('title'),
            playlist_description=clean_html(serie_data.get('description')),
            playlist_count=len(video_data),
        )


class BibelTvLiveIE(BibelTVIE):
    _VALID_URL = r'https?://(?:www\.)?bibeltv\.de/livestreams/(?P<id>[a-z]+)'
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
        json_btv_data = self._search_json(
            r'\s*data\s*=', webpage, 'bibeltvData', stream_id,
            transform_source=lambda x: js_to_json(x.replace('`', "'")))
        stream_data = json_btv_data.get(stream_id)
        if not stream_data:
            raise ExtractorError(f'Missing livestream data for {stream_id!r}')

        formats, subtitles = self._extract_formats_and_subtitles(
            stream_data.get('src', ()), stream_id, is_live=True)

        return {
            'id': stream_id,
            'title': stream_data.get('title'),
            'thumbnail': stream_data.get('poster'),
            'is_live': True,
            'formats': formats,
            'subtitles': subtitles,
        }
