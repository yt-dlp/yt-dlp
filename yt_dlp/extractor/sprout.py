from .adobepass import AdobePassIE
from ..utils import (
    int_or_none,
    smuggle_url,
    update_url_query,
)


class SproutIE(AdobePassIE):
    _VALID_URL = r'https?://(?:www\.)?(?:sproutonline|universalkids)\.com/(?:watch|(?:[^/]+/)*videos)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.universalkids.com/shows/remy-and-boo/season/1/videos/robot-bike-race',
        'info_dict': {
            'id': 'bm0foJFaTKqb',
            'ext': 'mp4',
            'title': 'Robot Bike Race',
            'description': 'md5:436b1d97117cc437f54c383f4debc66d',
            'timestamp': 1606148940,
            'upload_date': '20201123',
            'uploader': 'NBCU-MPAT',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.sproutonline.com/watch/cowboy-adventure',
        'only_matching': True,
    }, {
        'url': 'https://www.universalkids.com/watch/robot-bike-race',
        'only_matching': True,
    }]
    _GEO_COUNTRIES = ['US']

    def _real_extract(self, url):
        display_id = self._match_id(url)
        mpx_metadata = self._download_json(
            # http://nbcuunikidsprod.apps.nbcuni.com/networks/universalkids/content/videos/
            'https://www.universalkids.com/_api/videos/' + display_id,
            display_id)['mpxMetadata']
        media_pid = mpx_metadata['mediaPid']
        theplatform_url = 'https://link.theplatform.com/s/HNK2IC/' + media_pid
        query = {
            'mbr': 'true',
            'manifest': 'm3u',
        }
        if mpx_metadata.get('entitlement') == 'auth':
            query['auth'] = self._extract_mvpd_auth(url, media_pid, 'sprout', 'sprout')
        theplatform_url = smuggle_url(
            update_url_query(theplatform_url, query), {
                'force_smil_url': True,
                'geo_countries': self._GEO_COUNTRIES,
            })
        return {
            '_type': 'url_transparent',
            'id': media_pid,
            'url': theplatform_url,
            'series': mpx_metadata.get('seriesName'),
            'season_number': int_or_none(mpx_metadata.get('seasonNumber')),
            'episode_number': int_or_none(mpx_metadata.get('episodeNumber')),
            'ie_key': 'ThePlatform',
        }
