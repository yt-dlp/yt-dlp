# coding: utf-8
from __future__ import unicode_literals

from .adobepass import AdobePassIE
from ..utils import (
    extract_attributes,
    int_or_none,
    parse_age_limit,
    smuggle_url,
    update_url_query,
)


class FXNetworksIE(AdobePassIE):
    _VALID_URL = r'https?://(?:www\.)?(?:fxnetworks|simpsonsworld)\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.fxnetworks.com/video/1032565827847',
        'md5': '8d99b97b4aa7a202f55b6ed47ea7e703',
        'info_dict': {
            'id': 'dRzwHC_MMqIv',
            'ext': 'mp4',
            'title': 'First Look: Better Things - Season 2',
            'description': 'Because real life is like a fart. Watch this FIRST LOOK to see what inspired the new season of Better Things.',
            'age_limit': 14,
            'uploader': 'NEWA-FNG-FX',
            'upload_date': '20170825',
            'timestamp': 1503686274,
            'episode_number': 0,
            'season_number': 2,
            'series': 'Better Things',
        },
        'add_ie': ['ThePlatform'],
    }, {
        'url': 'http://www.simpsonsworld.com/video/716094019682',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        if 'The content you are trying to access is not available in your region.' in webpage:
            self.raise_geo_restricted()
        video_data = extract_attributes(self._search_regex(
            r'(<a.+?rel="https?://link\.theplatform\.com/s/.+?</a>)', webpage, 'video data'))
        player_type = self._search_regex(r'playerType\s*=\s*[\'"]([^\'"]+)', webpage, 'player type', default=None)
        release_url = video_data['rel']
        title = video_data['data-title']
        rating = video_data.get('data-rating')
        query = {
            'mbr': 'true',
        }
        if player_type == 'movies':
            query.update({
                'manifest': 'm3u',
            })
        else:
            query.update({
                'switch': 'http',
            })
        if video_data.get('data-req-auth') == '1':
            resource = self._get_mvpd_resource(
                video_data['data-channel'], title,
                video_data.get('data-guid'), rating)
            query['auth'] = self._extract_mvpd_auth(url, video_id, 'fx', resource)

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'title': title,
            'url': smuggle_url(update_url_query(release_url, query), {'force_smil_url': True}),
            'series': video_data.get('data-show-title'),
            'episode_number': int_or_none(video_data.get('data-episode')),
            'season_number': int_or_none(video_data.get('data-season')),
            'thumbnail': video_data.get('data-large-thumb'),
            'age_limit': parse_age_limit(rating),
            'ie_key': 'ThePlatform',
        }
