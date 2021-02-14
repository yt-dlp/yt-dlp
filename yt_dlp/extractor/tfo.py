# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    HEADRequest,
    ExtractorError,
    int_or_none,
    clean_html,
)


class TFOIE(InfoExtractor):
    _GEO_COUNTRIES = ['CA']
    _VALID_URL = r'https?://(?:www\.)?tfo\.org/(?:en|fr)/(?:[^/]+/){2}(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.tfo.org/en/universe/tfo-247/100463871/video-game-hackathon',
        'md5': 'cafbe4f47a8dae0ca0159937878100d6',
        'info_dict': {
            'id': '7da3d50e495c406b8fc0b997659cc075',
            'ext': 'mp4',
            'title': 'Video Game Hackathon',
            'description': 'md5:558afeba217c6c8d96c60e5421795c07',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._request_webpage(HEADRequest('http://www.tfo.org/'), video_id)
        infos = self._download_json(
            'http://www.tfo.org/api/web/video/get_infos', video_id, data=json.dumps({
                'product_id': video_id,
            }).encode(), headers={
                'X-tfo-session': self._get_cookies('http://www.tfo.org/')['tfo-session'].value,
            })
        if infos.get('success') == 0:
            if infos.get('code') == 'ErrGeoBlocked':
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            raise ExtractorError('%s said: %s' % (self.IE_NAME, clean_html(infos['msg'])), expected=True)
        video_data = infos['data']

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': 'limelight:media:' + video_data['llid'],
            'title': video_data['title'],
            'description': video_data.get('description'),
            'series': video_data.get('collection'),
            'season_number': int_or_none(video_data.get('season')),
            'episode_number': int_or_none(video_data.get('episode')),
            'duration': int_or_none(video_data.get('duration')),
            'ie_key': 'LimelightMedia',
        }
