import functools
import json

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    float_or_none,
    traverse_obj,
    unified_strdate,
)


class GronkhIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gronkh\.tv/stream/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://gronkh.tv/stream/657',
        'info_dict': {
            'id': '657',
            'ext': 'mp4',
            'title': 'Die Wilde H.O.R.D.E. 🎲 DAS ZWEiTE ZEiTALTER - Teil 1',
            'view_count': int,
            'thumbnail': r're:https://\d+\.cdn\.vod\.farm/preview/9e2555d3a23bf4e5c5b7c6b3b70a9d84\.jpg',
            'upload_date': '20221111',
            'chapters': 'count:3',
            'duration': 31463,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://gronkh.tv/stream/536',
        'info_dict': {
            'id': '536',
            'ext': 'mp4',
            'title': 'MARTHA IS DEAD  #FREiAB1830 ',
            'view_count': int,
            'thumbnail': r're:https://\d+\.cdn\.vod\.farm/preview/6436746cce14e25f751260a692872b9b\.jpg',
            'upload_date': '20211001',
            'duration': 32058,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://gronkh.tv/stream/546',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data_json = self._download_json(f'https://backend.gronkh.tv/v3/videos/episode/{video_id}', video_id)['data']
        m3u8_url = traverse_obj(data_json, ('urls', 'playlist'))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id)
        if traverse_obj(data_json, ('urls', 'vtt')):
            subtitles.setdefault('en', []).append({
                'url': traverse_obj(data_json, ('urls', 'vtt')),
                'ext': 'vtt',
            })
        return {
            'id': video_id,
            'title': data_json.get('title'),
            'view_count': data_json.get('views'),
            'thumbnail': traverse_obj(data_json, ('urls', 'thumbnail')),
            'upload_date': unified_strdate(data_json.get('created_at')),
            'formats': formats,
            'subtitles': subtitles,
            'duration': float_or_none(traverse_obj(data_json, ('meta', 'duration'))),
            'chapters': traverse_obj(data_json, (
                'chapters', lambda _, v: float_or_none(v['start_offset']) is not None, {
                    'title': ('category', 'title'),
                    'start_time': ('start_offset', {float_or_none}),
                })) or None,
        }


class GronkhFeedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gronkh\.tv(?:/landing)?/?(?:#|$)'
    IE_NAME = 'gronkh:feed'

    _TESTS = [{
        'url': 'https://gronkh.tv/landing',
        'info_dict': {
            'id': 'feed',
        },
        'playlist_count': 16,
    }, {
        'url': 'https://gronkh.tv',
        'only_matching': True,
    }]

    def _entries(self):
        for type_ in ('newest', 'hot'):
            info = self._download_json(
                f'https://backend.gronkh.tv/v3/videos/discovery/{type_}', 'feed', note=f'Downloading {type_} API JSON')
            for item in traverse_obj(info, ('data', ...)) or []:
                yield self.url_result(f'https://gronkh.tv/stream/{item["episode"]}', GronkhIE, item.get('title'))

    def _real_extract(self, url):
        return self.playlist_result(self._entries(), 'feed')


class GronkhVodsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gronkh\.tv/streams/?(?:#|$)'
    IE_NAME = 'gronkh:vods'

    _TESTS = [{
        'url': 'https://gronkh.tv/streams',
        'info_dict': {
            'id': 'vods',
        },
        'playlist_mincount': 150,
    }]
    _PER_PAGE = 20

    def _fetch_page(self, page):
        data = self._download_json(
            'https://backend.gronkh.tv/v3/videos/search', 'vods',
            note=f'Downloading stream video page {page + 1}',
            data=json.dumps({'order': 'created_at', 'dir': 'desc', 'page': page + 1}).encode(),
            headers={'Content-Type': 'application/json'})
        for item in traverse_obj(data, ('data', ...)) or []:
            yield self.url_result(f'https://gronkh.tv/stream/{item["episode"]}', GronkhIE, item['episode'], item.get('title'))

    def _real_extract(self, url):
        entries = OnDemandPagedList(functools.partial(self._fetch_page), self._PER_PAGE)
        return self.playlist_result(entries, 'vods')
