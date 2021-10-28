# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class MLSSoccerIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)(?:www\.)?mlssoccer\.com/video/[^#]+#(?P<id>[^/&$#?]+)'

    _TESTS = [{
        'url': 'https://www.mlssoccer.com/video/the-octagon-can-alphonso-davies-lead-canada-to-first-world-cup-since-1986#the-octagon-can-alphonso-davies-lead-canada-to-first-world-cup-since-1986',
        'info_dict': {
            'id': '6276033198001',
            'ext': 'mp4',
            'title': 'The Octagon | Can Alphonso Davies lead Canada to first World Cup since 1986?',
            'description': 'md5:f0a883ee33592a0221798f451a98be8f',
            'thumbnail': 'https://cf-images.us-east-1.prod.boltdns.net/v1/static/5530036772001/1bbc44f6-c63c-4981-82fa-46b0c1f891e0/5c1ca44a-a033-4e98-b531-ff24c4947608/160x90/match/image.jpg',
            'duration': 350.165,
            'timestamp': 1633627291,
            'uploader_id': '5530036772001',
            'tags': ['club/canada'],
            'is_live': False,
            'duration_string': '5:50',
            'upload_date': '20211007',
            'filesize_approx': 255193528.83200002
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        data_json = self._parse_json(self._html_search_regex(r'data-options\=\"([^\"]+)\"', webpage, 'json'), id)['videoList'][0]
        return {
            'id': id,
            '_type': 'url_transparent',
            'url': 'https://players.brightcove.net/%s/default_default/index.html?videoId=%s' % (data_json['accountId'], data_json['videoId']),
            'ie_key': 'BrightcoveNew',
        }
