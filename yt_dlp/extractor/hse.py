from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    unified_timestamp,
)


class HSEShowBaseInfoExtractor(InfoExtractor):
    _GEO_COUNTRIES = ['DE']

    def _extract_redux_data(self, url, video_id):
        webpage = self._download_webpage(url, video_id)
        redux = self._html_search_regex(
            r'window\.__REDUX_DATA__\s*=\s*({.*});?', webpage, 'redux data')
        return self._parse_json(redux.replace('\n', ''), video_id)

    def _extract_formats_and_subtitles(self, sources, video_id):
        if not sources:
            raise ExtractorError('No video found', expected=True, video_id=video_id)
        formats, subtitles = [], {}
        for src in sources:
            if src['mimetype'] != 'application/x-mpegURL':
                continue
            fmts, subs = self._extract_m3u8_formats_and_subtitles(src['url'], video_id, ext='mp4')
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        self._sort_formats(formats)
        return formats, subtitles


class HSEShowIE(HSEShowBaseInfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hse\.de/dpl/c/tv-shows/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.hse.de/dpl/c/tv-shows/505350',
        'info_dict': {
            'id': '505350',
            'ext': 'mp4',
            'title': 'Pfeffinger Mode & Accessoires',
            'timestamp': 1638810000,
            'upload_date': '20211206',
            'channel': 'HSE24',
            'uploader': 'Arina Pirayesh'
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._extract_redux_data(url, video_id)
        formats, subtitles = self._extract_formats_and_subtitles(
            traverse_obj(json_data, ('tvShowPage', 'tvShowVideo', 'sources')), video_id)

        show = traverse_obj(json_data, ('tvShowPage', 'tvShow')) or {}
        return {
            'id': video_id,
            'title': show.get('title') or video_id,
            'formats': formats,
            'timestamp': unified_timestamp(f'{show.get("date")} {show.get("hour")}:00'),
            'thumbnail': traverse_obj(json_data, ('tvShowVideo', 'poster')),
            'channel': self._search_regex(
                r'tvShow \| ([A-Z0-9]+)_', show.get('actionFieldText') or '', video_id, fatal=False),
            'uploader': show.get('presenter'),
            'subtitles': subtitles,
        }


class HSEProductIE(HSEShowBaseInfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hse\.de/dpl/p/product/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.hse.de/dpl/p/product/408630',
        'info_dict': {
            'id': '408630',
            'ext': 'mp4',
            'title': 'Hose im Ponte-Mix',
            'uploader': 'Judith Williams'
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._extract_redux_data(url, video_id)
        video = traverse_obj(json_data, ('productContent', 'productContent', 'videos', 0)) or {}
        formats, subtitles = self._extract_formats_and_subtitles(video.get('sources'), video_id)

        return {
            'id': video_id,
            'title': traverse_obj(json_data, ('productDetail', 'product', 'name', 'short')) or video_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': video.get('poster'),
            'uploader': traverse_obj(json_data, ('productDetail', 'product', 'brand', 'brandName')),
        }
