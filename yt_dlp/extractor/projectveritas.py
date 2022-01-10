# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    unified_strdate,
)


class ProjectVeritasIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?projectveritas\.com/(?P<type>news|video)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.projectveritas.com/news/exclusive-inside-the-new-york-and-new-jersey-hospitals-battling-coronavirus/',
        'info_dict': {
            'id': '51910aab-365a-5cf1-88f2-8eb1ca5fd3c6',
            'ext': 'mp4',
            'title': 'Exclusive: Inside The New York and New Jersey Hospitals Battling Coronavirus',
            'upload_date': '20200327',
            'thumbnail': 'md5:6076477fe50b03eb8708be9415e18e1c',
        }
    }, {
        'url': 'https://www.projectveritas.com/video/ilhan-omar-connected-ballot-harvester-in-cash-for-ballots-scheme-car-is-full/',
        'info_dict': {
            'id': 'c5aab304-a56b-54b1-9f0b-03b77bc5f2f6',
            'ext': 'mp4',
            'title': 'Ilhan Omar connected Ballot Harvester in cash-for-ballots scheme: "Car is full" of absentee ballots',
            'upload_date': '20200927',
            'thumbnail': 'md5:194b8edf0e2ba64f25500ff4378369a4',
        }
    }]

    def _real_extract(self, url):
        id, type = self._match_valid_url(url).group('id', 'type')
        api_url = f'https://www.projectveritas.com/page-data/{type}/{id}/page-data.json'
        data_json = self._download_json(api_url, id)['result']['data']
        main_data = traverse_obj(data_json, 'video', 'post')
        video_id = main_data['id']
        thumbnail = traverse_obj(main_data, ('image', 'ogImage', 'src'))
        mux_asset = traverse_obj(main_data,
                                 'muxAsset', ('body', 'json', 'content', ..., 'data', 'target', 'fields', 'muxAsset'),
                                 get_all=False, expected_type=dict)
        if not mux_asset:
            raise ExtractorError('No video on the provided url.', expected=True)
        playback_id = traverse_obj(mux_asset, 'playbackId', ('en-US', 'playbackId'))
        formats = self._extract_m3u8_formats(f'https://stream.mux.com/{playback_id}.m3u8', video_id)
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': main_data['title'],
            'upload_date': unified_strdate(main_data.get('date')),
            'thumbnail': thumbnail.replace('//', ''),
            'formats': formats,
        }
