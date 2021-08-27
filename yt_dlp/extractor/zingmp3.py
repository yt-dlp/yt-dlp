# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    int_or_none,
)


class ZingMp3BaseIE(InfoExtractor):
    _VALID_URL_TMPL = r'https?://(?:mp3\.zing|zingmp3)\.vn/(?:%s)/[^/]+/(?P<id>\w+)\.html'
    _GEO_COUNTRIES = ['VN']

    def _extract_item(self, item, fatal):
        item_id = item['id']
        title = item.get('name') or item['title']

        formats = []
        for k, v in (item.get('source') or {}).items():
            if not v:
                continue
            if k in ('mp4', 'hls'):
                for res, video_url in v.items():
                    if not video_url:
                        continue
                    if k == 'hls':
                        formats.extend(self._extract_m3u8_formats(
                            video_url, item_id, 'mp4',
                            'm3u8_native', m3u8_id=k, fatal=False))
                    elif k == 'mp4':
                        formats.append({
                            'format_id': 'mp4-' + res,
                            'url': video_url,
                            'height': int_or_none(self._search_regex(
                                r'^(\d+)p', res, 'resolution', default=None)),
                        })
            else:
                formats.append({
                    'ext': 'mp3',
                    'format_id': k,
                    'tbr': int_or_none(k),
                    'url': self._proto_relative_url(v),
                    'vcodec': 'none',
                })
        if not formats:
            if not fatal:
                return
            msg = item['msg']
            if msg == 'Sorry, this content is not available in your country.':
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)
            self.raise_no_formats(msg, expected=True)
        self._sort_formats(formats)

        subtitles = None
        lyric = item.get('lyric')
        if lyric:
            subtitles = {
                'origin': [{
                    'url': lyric,
                }],
            }

        album = item.get('album') or {}

        return {
            'id': item_id,
            'title': title,
            'formats': formats,
            'thumbnail': item.get('thumbnail'),
            'subtitles': subtitles,
            'duration': int_or_none(item.get('duration')),
            'track': title,
            'artist': item.get('artists_names'),
            'album': album.get('name') or album.get('title'),
            'album_artist': album.get('artists_names'),
        }

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(
            url.replace('://zingmp3.vn/', '://mp3.zing.vn/'),
            page_id, query={'play_song': 1})
        data_path = self._search_regex(
            r'data-xml="([^"]+)', webpage, 'data path')
        return self._process_data(self._download_json(
            'https://mp3.zing.vn/xhr' + data_path, page_id)['data'])


class ZingMp3IE(ZingMp3BaseIE):
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'bai-hat|video-clip'
    _TESTS = [{
        'url': 'http://mp3.zing.vn/bai-hat/Xa-Mai-Xa-Bao-Thy/ZWZB9WAB.html',
        'md5': 'ead7ae13693b3205cbc89536a077daed',
        'info_dict': {
            'id': 'ZWZB9WAB',
            'title': 'Xa Mãi Xa',
            'ext': 'mp3',
            'thumbnail': r're:^https?://.+\.jpg',
            'subtitles': {
                'origin': [{
                    'ext': 'lrc',
                }]
            },
            'duration': 255,
            'track': 'Xa Mãi Xa',
            'artist': 'Bảo Thy',
            'album': 'Special Album',
            'album_artist': 'Bảo Thy',
        },
    }, {
        'url': 'https://mp3.zing.vn/video-clip/Suong-Hoa-Dua-Loi-K-ICM-RYO/ZO8ZF7C7.html',
        'md5': 'e9c972b693aa88301ef981c8151c4343',
        'info_dict': {
            'id': 'ZO8ZF7C7',
            'title': 'Sương Hoa Đưa Lối',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.+\.jpg',
            'duration': 207,
            'track': 'Sương Hoa Đưa Lối',
            'artist': 'K-ICM, RYO',
        },
    }, {
        'url': 'https://zingmp3.vn/bai-hat/Xa-Mai-Xa-Bao-Thy/ZWZB9WAB.html',
        'only_matching': True,
    }]
    IE_NAME = 'zingmp3'
    IE_DESC = 'mp3.zing.vn'

    def _process_data(self, data):
        return self._extract_item(data, True)


class ZingMp3AlbumIE(ZingMp3BaseIE):
    _VALID_URL = ZingMp3BaseIE._VALID_URL_TMPL % 'album|playlist'
    _TESTS = [{
        'url': 'http://mp3.zing.vn/album/Lau-Dai-Tinh-Ai-Bang-Kieu-Minh-Tuyet/ZWZBWDAF.html',
        'info_dict': {
            '_type': 'playlist',
            'id': 'ZWZBWDAF',
            'title': 'Lâu Đài Tình Ái',
        },
        'playlist_count': 10,
    }, {
        'url': 'http://mp3.zing.vn/playlist/Duong-Hong-Loan-apollobee/IWCAACCB.html',
        'only_matching': True,
    }, {
        'url': 'https://zingmp3.vn/album/Lau-Dai-Tinh-Ai-Bang-Kieu-Minh-Tuyet/ZWZBWDAF.html',
        'only_matching': True,
    }]
    IE_NAME = 'zingmp3:album'

    def _process_data(self, data):
        def entries():
            for item in (data.get('items') or []):
                entry = self._extract_item(item, False)
                if entry:
                    yield entry
        info = data.get('info') or {}
        return self.playlist_result(
            entries(), info.get('id'), info.get('name') or info.get('title'))
