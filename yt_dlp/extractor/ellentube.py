# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    float_or_none,
    int_or_none,
    try_get,
)


class EllenTubeBaseIE(InfoExtractor):
    def _extract_data_config(self, webpage, video_id):
        details = self._search_regex(
            r'(<[^>]+\bdata-component=(["\'])[Dd]etails.+?></div>)', webpage,
            'details')
        return self._parse_json(
            extract_attributes(details)['data-config'], video_id)

    def _extract_video(self, data, video_id):
        title = data['title']

        formats = []
        duration = None
        for entry in data.get('media'):
            if entry.get('id') == 'm3u8':
                formats = self._extract_m3u8_formats(
                    entry['url'], video_id, 'mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls')
                duration = int_or_none(entry.get('duration'))
                break
        self._sort_formats(formats)

        def get_insight(kind):
            return int_or_none(try_get(
                data, lambda x: x['insight']['%ss' % kind]))

        return {
            'extractor_key': EllenTubeIE.ie_key(),
            'id': video_id,
            'title': title,
            'description': data.get('description'),
            'duration': duration,
            'thumbnail': data.get('thumbnail'),
            'timestamp': float_or_none(data.get('publishTime'), scale=1000),
            'view_count': get_insight('view'),
            'like_count': get_insight('like'),
            'formats': formats,
        }


class EllenTubeIE(EllenTubeBaseIE):
    _VALID_URL = r'''(?x)
                        (?:
                            ellentube:|
                            https://api-prod\.ellentube\.com/ellenapi/api/item/
                        )
                        (?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})
                    '''
    _TESTS = [{
        'url': 'https://api-prod.ellentube.com/ellenapi/api/item/0822171c-3829-43bf-b99f-d77358ae75e3',
        'md5': '2fabc277131bddafdd120e0fc0f974c9',
        'info_dict': {
            'id': '0822171c-3829-43bf-b99f-d77358ae75e3',
            'ext': 'mp4',
            'title': 'Ellen Meets Las Vegas Survivors Jesus Campos and Stephen Schuck',
            'description': 'md5:76e3355e2242a78ad9e3858e5616923f',
            'thumbnail': r're:^https?://.+?',
            'duration': 514,
            'timestamp': 1508505120,
            'upload_date': '20171020',
            'view_count': int,
            'like_count': int,
        }
    }, {
        'url': 'ellentube:734a3353-f697-4e79-9ca9-bfc3002dc1e0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            'https://api-prod.ellentube.com/ellenapi/api/item/%s' % video_id,
            video_id)
        return self._extract_video(data, video_id)


class EllenTubeVideoIE(EllenTubeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?ellentube\.com/video/(?P<id>.+?)\.html'
    _TEST = {
        'url': 'https://www.ellentube.com/video/ellen-meets-las-vegas-survivors-jesus-campos-and-stephen-schuck.html',
        'only_matching': True,
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._extract_data_config(webpage, display_id)['id']
        return self.url_result(
            'ellentube:%s' % video_id, ie=EllenTubeIE.ie_key(),
            video_id=video_id)


class EllenTubePlaylistIE(EllenTubeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?ellentube\.com/(?:episode|studios)/(?P<id>.+?)\.html'
    _TESTS = [{
        'url': 'https://www.ellentube.com/episode/dax-shepard-jordan-fisher-haim.html',
        'info_dict': {
            'id': 'dax-shepard-jordan-fisher-haim',
            'title': "Dax Shepard, 'DWTS' Team Jordan Fisher & Lindsay Arnold, HAIM",
            'description': 'md5:bfc982194dabb3f4e325e43aa6b2e21c',
        },
        'playlist_count': 6,
    }, {
        'url': 'https://www.ellentube.com/studios/macey-goes-rving0.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        data = self._extract_data_config(webpage, display_id)['data']
        feed = self._download_json(
            'https://api-prod.ellentube.com/ellenapi/api/feed/?%s'
            % data['filter'], display_id)
        entries = [
            self._extract_video(elem, elem['id'])
            for elem in feed if elem.get('type') == 'VIDEO' and elem.get('id')]
        return self.playlist_result(
            entries, display_id, data.get('title'),
            clean_html(data.get('description')))
