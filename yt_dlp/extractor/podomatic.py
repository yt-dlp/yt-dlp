from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..utils import int_or_none


class PodomaticIE(InfoExtractor):
    IE_NAME = 'podomatic'
    _VALID_URL = r'''(?x)
                    (?P<proto>https?)://
                        (?:
                            (?P<channel>[^.]+)\.podomatic\.com/entry|
                            (?:www\.)?podomatic\.com/podcasts/(?P<channel_2>[^/]+)/episodes
                        )/
                        (?P<id>[^/?#&]+)
                '''

    _TESTS = [{
        'url': 'http://scienceteachingtips.podomatic.com/entry/2009-01-02T16_03_35-08_00',
        'md5': '84bb855fcf3429e6bf72460e1eed782d',
        'info_dict': {
            'id': '2009-01-02T16_03_35-08_00',
            'ext': 'mp3',
            'uploader': 'Science Teaching Tips',
            'uploader_id': 'scienceteachingtips',
            'title': '64.  When the Moon Hits Your Eye',
            'duration': 446,
        }
    }, {
        'url': 'http://ostbahnhof.podomatic.com/entry/2013-11-15T16_31_21-08_00',
        'md5': 'd2cf443931b6148e27638650e2638297',
        'info_dict': {
            'id': '2013-11-15T16_31_21-08_00',
            'ext': 'mp3',
            'uploader': 'Ostbahnhof / Techno Mix',
            'uploader_id': 'ostbahnhof',
            'title': 'Einunddreizig',
            'duration': 3799,
        }
    }, {
        'url': 'https://www.podomatic.com/podcasts/scienceteachingtips/episodes/2009-01-02T16_03_35-08_00',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        channel = mobj.group('channel') or mobj.group('channel_2')

        json_url = (('%s://%s.podomatic.com/entry/embed_params/%s'
                     + '?permalink=true&rtmp=0') %
                    (mobj.group('proto'), channel, video_id))
        data_json = self._download_webpage(
            json_url, video_id, 'Downloading video info')
        data = json.loads(data_json)

        video_url = data['downloadLink']
        if not video_url:
            video_url = '%s/%s' % (data['streamer'].replace('rtmp', 'http'), data['mediaLocation'])
        uploader = data['podcast']
        title = data['title']
        thumbnail = data['imageLocation']
        duration = int_or_none(data.get('length'), 1000)

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'uploader': uploader,
            'uploader_id': channel,
            'thumbnail': thumbnail,
            'duration': duration,
        }
