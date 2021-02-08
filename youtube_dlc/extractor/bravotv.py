# coding: utf-8
from __future__ import unicode_literals

import re

from .adobepass import AdobePassIE
from ..utils import (
    smuggle_url,
    update_url_query,
    int_or_none,
)


class BravoTVIE(AdobePassIE):
    _VALID_URL = r'https?://(?:www\.)?(?P<req_id>bravotv|oxygen)\.com/(?:[^/]+/)+(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.bravotv.com/top-chef/season-16/episode-15/videos/the-top-chef-season-16-winner-is',
        'md5': 'e34684cfea2a96cd2ee1ef3a60909de9',
        'info_dict': {
            'id': 'epL0pmK1kQlT',
            'ext': 'mp4',
            'title': 'The Top Chef Season 16 Winner Is...',
            'description': 'Find out who takes the title of Top Chef!',
            'uploader': 'NBCU-BRAV',
            'upload_date': '20190314',
            'timestamp': 1552591860,
        }
    }, {
        'url': 'http://www.bravotv.com/below-deck/season-3/ep-14-reunion-part-1',
        'only_matching': True,
    }, {
        'url': 'https://www.oxygen.com/in-ice-cold-blood/season-2/episode-16/videos/handling-the-horwitz-house-after-the-murder-season-2',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        site, display_id = re.match(self._VALID_URL, url).groups()
        webpage = self._download_webpage(url, display_id)
        settings = self._parse_json(self._search_regex(
            r'<script[^>]+data-drupal-selector="drupal-settings-json"[^>]*>({.+?})</script>', webpage, 'drupal settings'),
            display_id)
        info = {}
        query = {
            'mbr': 'true',
        }
        account_pid, release_pid = [None] * 2
        tve = settings.get('ls_tve')
        if tve:
            query['manifest'] = 'm3u'
            mobj = re.search(r'<[^>]+id="pdk-player"[^>]+data-url=["\']?(?:https?:)?//player\.theplatform\.com/p/([^/]+)/(?:[^/]+/)*select/([^?#&"\']+)', webpage)
            if mobj:
                account_pid, tp_path = mobj.groups()
                release_pid = tp_path.strip('/').split('/')[-1]
            else:
                account_pid = 'HNK2IC'
                tp_path = release_pid = tve['release_pid']
            if tve.get('entitlement') == 'auth':
                adobe_pass = settings.get('tve_adobe_auth', {})
                if site == 'bravotv':
                    site = 'bravo'
                resource = self._get_mvpd_resource(
                    adobe_pass.get('adobePassResourceId') or site,
                    tve['title'], release_pid, tve.get('rating'))
                query['auth'] = self._extract_mvpd_auth(
                    url, release_pid,
                    adobe_pass.get('adobePassRequestorId') or site, resource)
        else:
            shared_playlist = settings['ls_playlist']
            account_pid = shared_playlist['account_pid']
            metadata = shared_playlist['video_metadata'][shared_playlist['default_clip']]
            tp_path = release_pid = metadata.get('release_pid')
            if not release_pid:
                release_pid = metadata['guid']
                tp_path = 'media/guid/2140479951/' + release_pid
            info.update({
                'title': metadata['title'],
                'description': metadata.get('description'),
                'season_number': int_or_none(metadata.get('season_num')),
                'episode_number': int_or_none(metadata.get('episode_num')),
            })
            query['switch'] = 'progressive'
        info.update({
            '_type': 'url_transparent',
            'id': release_pid,
            'url': smuggle_url(update_url_query(
                'http://link.theplatform.com/s/%s/%s' % (account_pid, tp_path),
                query), {'force_smil_url': True}),
            'ie_key': 'ThePlatform',
        })
        return info
