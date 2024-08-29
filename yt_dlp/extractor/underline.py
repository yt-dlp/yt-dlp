import functools

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    filter_dict,
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
            'live_status': 'not_live',
        },
    }, {
        # PPT only
        'url': 'https://underline.io/events/342/posters/12863/poster/66459-low-resourced-multilingual-neural-machine-translation-for-ometo-english',
        'info_dict': {
            'id': '66459',
            'title': 'Low Resourced Multilingual Neural Machine Translation for Ometo-English',
            'thumbnail': 'https://assets.underline.io/lecture/66459/poster_document_thumbnail_extract/69a3fd48e3bb137ddcf3099db637d184.jpg',
            'live_status': 'not_live',
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

        m3u8_url = traverse_obj(data, (..., 'data', 'attributes', 'playlist', {url_or_none}), get_all=False)
        subtitle_urls = filter_dict(dict(traverse_obj(data, (
            ..., 'data', lambda _, v: v['type'] == 'transcripts', {lambda x: (
                x['relationships']['language']['data']['id'],
                url_or_none(x['attributes']['subtitleUrl']),
            )}))))

        return {
            'id': video_id,
            'title': traverse_obj(data, (..., 'data', 'attributes', 'title', {str}), get_all=False),
            'thumbnail': traverse_obj(data, (
                ..., 'data', 'attributes', 'originalPosterDocumentThumbnailExtractUrl', {url_or_none}), get_all=False),
            'formats': self._extract_m3u8_formats(m3u8_url, video_id) if m3u8_url else [],
            'subtitles': filter_dict(dict(traverse_obj(data, (
                ..., 'included', lambda _, v: v['type'] == 'transcript_languages', {lambda x: (
                    x['attributes']['locale'],
                    [{'url': subtitle_urls[x['id']]}],
                )})))),
            'live_status': 'not_live',
        }


class UnderlinePosterListIE(InfoExtractor):
    _VALID_URL = r'https://(?:www\.)?underline\.io/events/(?P<event_id>\d+)/posters/?\?(?:[^&]+&)*?eventSessionId=(?P<event_session_id>\d+)(?:&|#)?'
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

    def _fetch_paged_channel_video_list(self, list_url, event_id, event_session_id, page):
        page_num = page + 1
        video_url_tmpl = f'https://underline.io/events/{event_id}/posters/{event_session_id}/poster/{{id}}-{{slug}}'

        page_info = self._download_json(update_url(
            list_url, query_update={'page[number]': page_num}), event_session_id, headers=self._HEADERS,
            note=f'Downloading list info (page {page_num})', errnote=f'Failed to download list info (page {page_num})')

        yield from traverse_obj(page_info, (
            'data', ..., {lambda x: video_url_tmpl.format(id=x['id'], slug=x['attributes']['slug'])}, {self.url_result}))

    def _real_extract(self, url):
        event_id, event_session_id = self._match_valid_url(url).groups()

        event_info = self._download_json(
            f'https://app.underline.io/api/v1/thin_event_sessions/{event_session_id}', event_session_id, headers=self._HEADERS,
            note='Downloading event session info', errnote='Failed to download event session info')

        return self.playlist_result(OnDemandPagedList(functools.partial(
            self._fetch_paged_channel_video_list,
            update_url('https://app.underline.io/api/v1/thin_lectures', query_update={
                'filter[poster_lecture]': 'true',
                'filter[published]': 'all',
                'sort': 'held_at,id',
                'include': 'sorted_profiles,event_session,tag,event',
                'filter[scope]': 'all',
                'filter[event_id]': event_id,
                'filter[event_session_id]': event_session_id,
                'page[size]': self._PAGE_SIZE,
            }), event_id, event_session_id), self._PAGE_SIZE),
            event_session_id,
            traverse_obj(event_info, ('data', 'attributes', 'name'), get_all=False),
            traverse_obj(event_info, ('data', 'attributes', 'description'), get_all=False))
