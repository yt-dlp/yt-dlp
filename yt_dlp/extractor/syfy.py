from .adobepass import AdobePassIE
from ..utils import (
    update_url_query,
    smuggle_url,
)


class SyfyIE(AdobePassIE):
    _VALID_URL = r'https?://(?:www\.)?syfy\.com/(?:[^/]+/)?videos/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'http://www.syfy.com/theinternetruinedmylife/videos/the-internet-ruined-my-life-season-1-trailer',
        'info_dict': {
            'id': '2968097',
            'ext': 'mp4',
            'title': 'The Internet Ruined My Life: Season 1 Trailer',
            'description': 'One tweet, one post, one click, can destroy everything.',
            'uploader': 'NBCU-MPAT',
            'upload_date': '20170113',
            'timestamp': 1484345640,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['ThePlatform'],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        syfy_mpx = list(self._parse_json(self._search_regex(
            r'jQuery\.extend\(Drupal\.settings\s*,\s*({.+?})\);', webpage, 'drupal settings'),
            display_id)['syfy']['syfy_mpx'].values())[0]
        video_id = syfy_mpx['mpxGUID']
        title = syfy_mpx['episodeTitle']
        query = {
            'mbr': 'true',
            'manifest': 'm3u',
        }
        if syfy_mpx.get('entitlement') == 'auth':
            resource = self._get_mvpd_resource(
                'syfy', title, video_id,
                syfy_mpx.get('mpxRating', 'TV-14'))
            query['auth'] = self._extract_mvpd_auth(
                url, video_id, 'syfy', resource)

        return {
            '_type': 'url_transparent',
            'ie_key': 'ThePlatform',
            'url': smuggle_url(update_url_query(
                self._proto_relative_url(syfy_mpx['releaseURL']), query),
                {'force_smil_url': True}),
            'title': title,
            'id': video_id,
            'display_id': display_id,
        }
