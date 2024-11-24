import functools

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    filter_dict,
    merge_dicts,
    update_url,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class UnderlinePosterIE(InfoExtractor):
    _VALID_URL = r'https://(?:www\.)?underline\.io/events/\d+/posters/\d+/poster/(?P<id>\d+)-[\w-]+/?(?:[#?]|$)'
    _TESTS = [{
        # Video and PPT
        'url': 'https://underline.io/events/342/posters/12863/poster/66466-towards-a-general-purpose-machine-translation-system-for-sranantongo',
        'info_dict': {
            'id': '66466',
            'ext': 'mp4',
            'title': 'Towards a general purpose machine translation system for Sranantongo',
            'thumbnail': 'https://assets.underline.io/lecture/66466/poster_document_thumbnail_extract/2a8d3abd5a5edbf0117d8d9bdf018e6d.jpg',
        },
    }, {
        # no video, PPT only
        'url': 'https://underline.io/events/342/posters/12863/poster/66459-low-resourced-multilingual-neural-machine-translation-for-ometo-english',
        'info_dict': {
            'id': '66459',
            'title': 'Low Resourced Multilingual Neural Machine Translation for Ometo-English',
            'thumbnail': 'https://assets.underline.io/lecture/66459/poster_document_thumbnail_extract/69a3fd48e3bb137ddcf3099db637d184.jpg',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['No video formats found!', 'Requested format is not available'],
    }, {
        'url': 'https://www.underline.io/events/342/posters/12863/poster/66463-mbti-personality-prediction-approach-on-persian-twitter/?tab=video',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['fallback']

        formats = traverse_obj(data, (
            ..., 'data', 'attributes', 'playlist', {url_or_none}, filter,
            {lambda x: self._extract_m3u8_formats(x, video_id)}, any))

        subtitles = {}
        subtitle_urls = traverse_obj(data, (..., 'data', lambda _, v: v['type'] == 'transcripts', {
            'id': ('relationships', 'language', 'data', 'id'),
            'url': ('attributes', 'subtitleUrl', {url_or_none}),
        }, {lambda x: {x['id']: x['url']}}, all, {lambda x: merge_dicts(*x)}, {filter_dict}), default={})
        if subtitle_urls:
            traverse_obj(data, (..., 'included', lambda _, v: v['type'] == 'transcript_languages', {
                'tag': ('attributes', 'locale'),
                'url': ('id', {subtitle_urls.get}),
            }, {filter_dict}, {lambda x: self._merge_subtitles({x['tag']: [{'url': x['url']}]}, target=subtitles)}))

        return {
            'id': video_id,
            'title': traverse_obj(data, (..., 'data', 'attributes', 'title', {str}, any)),
            'thumbnail': traverse_obj(data, (..., 'data', 'attributes', 'originalPosterDocumentThumbnailExtractUrl', {url_or_none}, any)),
            'formats': formats,
            'subtitles': subtitles,
        }


class UnderlinePosterListIE(InfoExtractor):
    _VALID_URL = r'https://(?:www\.)?underline\.io/events/(?P<event_id>\d+)/posters/?\?(?:[^&]+&)*?eventSessionId=(?P<session_id>\d+)(?:&|#)?'
    _HEADERS = {'Accept': 'application/vnd.api+json'}
    _PAGE_SIZE = 16
    _TESTS = [{
        'url': 'https://underline.io/events/342/posters?eventSessionId=12863',
        'info_dict': {
            'id': '12863',
            'title': 'W13 (WiNLP) The Sixth Widening NLP Workshop',
            'description': r're:.+Isidora Tourni and Surangika Ranathunga.+',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://www.underline.io/events/342/posters?searchGroup=lecture&eventSessionId=12860',
        'only_matching': True,
    }]

    def _fetch_paged_channel_video_list(self, list_url, event_id, session_id, page):
        page_num = page + 1
        video_url_tmpl = f'https://underline.io/events/{event_id}/posters/{session_id}/poster/{{id}}-{{slug}}'

        page_info = self._download_json(update_url(
            list_url, query_update={'page[number]': page_num}), session_id, headers=self._HEADERS,
            note=f'Downloading list info (page {page_num})', errnote=f'Failed to download list info (page {page_num})')

        yield from traverse_obj(page_info, (
            'data', ..., {lambda x: video_url_tmpl.format(id=x['id'], slug=x['attributes']['slug'])}, {self.url_result}))

    def _real_extract(self, url):
        event_id, session_id = self._match_valid_url(url).groups()

        session_info = {
            **traverse_obj(self._download_json(
                f'https://app.underline.io/api/v1/thin_event_sessions/{session_id}', session_id,
                headers=self._HEADERS, note='Downloading session info', errnote='Failed to download session info'), ({
                    'title': ('data', 'attributes', 'name'),
                    'description': ('data', 'attributes', 'description'),
                }, any)),
            'id': session_id,
        }

        return self.playlist_result(OnDemandPagedList(functools.partial(
            self._fetch_paged_channel_video_list,
            update_url('https://app.underline.io/api/v1/thin_lectures', query_update={
                'filter[poster_lecture]': 'true',
                'filter[published]': 'all',
                'sort': 'held_at,id',
                'include': 'sorted_profiles,event_session,tag,event',
                'filter[scope]': 'all',
                'filter[event_id]': event_id,
                'filter[event_session_id]': session_id,
                'page[size]': self._PAGE_SIZE,
            }), event_id, session_id), self._PAGE_SIZE),
            **session_info)
