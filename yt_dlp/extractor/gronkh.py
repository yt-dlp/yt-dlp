import functools

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    float_or_none,
    traverse_obj,
    unified_strdate,
)


class GronkhIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gronkh\.tv/(?:watch/)?streams?/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://gronkh.tv/streams/657',
        'info_dict': {
            'id': '657',
            'ext': 'mp4',
            'title': 'H.O.R.D.E. - DAS ZWEiTE ZEiTALTER 🎲 Session 1',
            'view_count': int,
            'thumbnail': 'https://01.cdn.vod.farm/preview/9e2555d3a23bf4e5c5b7c6b3b70a9d84.jpg',
            'upload_date': '20221111',
            'chapters': 'count:3',
            'duration': 31463,
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://gronkh.tv/stream/536',
        'info_dict': {
            'id': '536',
            'ext': 'mp4',
            'title': 'GTV0536, 2021-10-01 - MARTHA IS DEAD  #FREiAB1830  !FF7 !horde !archiv',
            'view_count': int,
            'thumbnail': 'https://01.cdn.vod.farm/preview/6436746cce14e25f751260a692872b9b.jpg',
            'upload_date': '20211001',
            'duration': 32058,
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://gronkh.tv/watch/stream/546',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        data_json = self._download_json(f'https://api.gronkh.tv/v1/video/info?episode={id}', id)
        m3u8_url = self._download_json(f'https://api.gronkh.tv/v1/video/playlist?episode={id}', id)['playlist_url']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, id)
        if data_json.get('vtt_url'):
            subtitles.setdefault('en', []).append({
                'url': data_json['vtt_url'],
                'ext': 'vtt',
            })
        return {
            'id': id,
            'title': data_json.get('title'),
            'view_count': data_json.get('views'),
            'thumbnail': data_json.get('preview_url'),
            'upload_date': unified_strdate(data_json.get('created_at')),
            'formats': formats,
            'subtitles': subtitles,
            'duration': float_or_none(data_json.get('source_length')),
            'chapters': traverse_obj(data_json, (
                'chapters', lambda _, v: float_or_none(v['offset']) is not None, {
                    'title': 'title',
                    'start_time': ('offset', {float_or_none}),
                })) or None,
        }


class GronkhFeedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gronkh\.tv(?:/feed)?/?(?:#|$)'
    IE_NAME = 'gronkh:feed'

    _TESTS = [{
        'url': 'https://gronkh.tv/feed',
        'info_dict': {
            'id': 'feed',
        },
        'playlist_count': 16,
    }, {
        'url': 'https://gronkh.tv',
        'only_matching': True,
    }]

    def _entries(self):
        for type_ in ('recent', 'views'):
            info = self._download_json(
                f'https://api.gronkh.tv/v1/video/discovery/{type_}', 'feed', note=f'Downloading {type_} API JSON')
            for item in traverse_obj(info, ('discovery', ...)) or []:
                yield self.url_result(f'https://gronkh.tv/watch/stream/{item["episode"]}', GronkhIE, item.get('title'))

    def _real_extract(self, url):
        return self.playlist_result(self._entries(), 'feed')


class GronkhVodsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gronkh\.tv/vods/streams/?(?:#|$)'
    IE_NAME = 'gronkh:vods'

    _TESTS = [{
        'url': 'https://gronkh.tv/vods/streams',
        'info_dict': {
            'id': 'vods',
        },
        'playlist_mincount': 150,
    }]
    _PER_PAGE = 25

    def _fetch_page(self, page):
        items = traverse_obj(self._download_json(
            'https://api.gronkh.tv/v1/search', 'vods', query={'offset': self._PER_PAGE * page, 'first': self._PER_PAGE},
            note=f'Downloading stream video page {page + 1}'), ('results', 'videos', ...))
        for item in items or []:
            yield self.url_result(f'https://gronkh.tv/watch/stream/{item["episode"]}', GronkhIE, item['episode'], item.get('title'))

    def _real_extract(self, url):
        entries = OnDemandPagedList(functools.partial(self._fetch_page), self._PER_PAGE)
        return self.playlist_result(entries, 'vods')
