import re

import requests

from .dplay import DPlayIE
from ..compat import compat_urlparse
from ..utils import (
    ExtractorError,
)


def _generate_video_specific_cache_url(slug, parent_slug):
    """
    Generate the MAGIC string for the video specific cache url.

    :param slug: The part of the url that identifies the video by title.
    :param parent_slug: The part of the url that identifies the PARENT directory.
    :return: The generated url.
    """
    return 'https://de-api.loma-cms.com/feloma/page/{0}/?environment=tele5&parent_slug={1}&v=2'.format(slug,
                                                                                                       parent_slug)
def _do_cached_post(s: requests.session,
                    referer: str,
                    url: str) -> dict:
    """
    Do the API call to CACHED json endpoint.

    It is likely connected to the new "loma-cms" API.

    :param s: The session we use.
    :param referer: The referer url.
    :param url: The url to retrieve the cached data for.
    :return: The json dict from the response.
    """
    r = s.post(url='https://tele5.de/cached',
               headers={
                   'Origin': 'https://tele5.de',
                   'Referer': referer,
                   # Referer is a mandatory key,
                   'User-Agent': 'Youtube-DL',
                   # User-Agent is a mandatory key, it can be anything!
               },
               json={'path': url}
               )
    r.raise_for_status()
    return r.json()

class Tele5IE(DPlayIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?://(?:www\.)?tele5\.de/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _GEO_COUNTRIES = ['DE']
    _TESTS = [{
        'url': 'https://tele5.de/mediathek/sorority-babes-in-the-slimeball-bowl-o-rama',
        'info_dict': {
            'id': '5582852',
            'title': 'Sorority Babes in the Slimeball Bowl-O-Rama',
            'ext': 'mp4',
            'series': 'Sorority Babes in the Slimeball Bowl-O-Rama',
            'duration': 4779.88,
            'description': 'md5:1d8d30ed3d221613861aaefa8d7e887e',
            'timestamp': 1697839800,
            'upload_date': '20231020',
            'creator': 'Tele5',
            'tags': [],
            'thumbnail': 'https://eu1-prod-images.disco-api.com/2023/10/02/501fa839-d3ac-3c04-aa61-57f98802c532.jpeg',
        },
    }, {
        'url': 'https://www.tele5.de/mediathek/filme-online/videos?vid=1549416',
        'only_matching': True,
        'info_dict': {
            'id': '1549416',
            'ext': 'mp4',
            'upload_date': '20180814',
            'timestamp': 1534290623,
            'title': 'Pandorum',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'No longer available: "404 Seite nicht gefunden"',
    }, {
        # jwplatform, nexx unavailable
        'url': 'https://www.tele5.de/filme/ghoul-das-geheimnis-des-friedhofmonsters/',
        'only_matching': True,
        'info_dict': {
            'id': 'WJuiOlUp',
            'ext': 'mp4',
            'upload_date': '20200603',
            'timestamp': 1591214400,
            'title': 'Ghoul - Das Geheimnis des Friedhofmonsters',
            'description': 'md5:42002af1d887ff3d5b2b3ca1f8137d97',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'No longer available, redirects to Filme page',
    }, {
        'url': 'https://tele5.de/mediathek/angel-of-mine/',
        'only_matching': True,
        'info_dict': {
            'id': '1252360',
            'ext': 'mp4',
            'upload_date': '20220109',
            'timestamp': 1641762000,
            'title': 'Angel of Mine',
            'description': 'md5:a72546a175e1286eb3251843a52d1ad7',
        },
        'params': {
            'format': 'bestvideo',
        },
    }, {
        'url': 'https://www.tele5.de/kalkofes-mattscheibe/video-clips/politik-und-gesellschaft?ve_id=1551191',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/video-clip/?ve_id=1609440',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/filme/schlefaz-dragon-crusaders/',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/filme/making-of/avengers-endgame/',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/star-trek/raumschiff-voyager/ganze-folge/das-vinculum/',
        'only_matching': True,
    }, {
        'url': 'https://www.tele5.de/anders-ist-sevda/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        content_regex = re.compile(r'https?://(?:www\.)?(?P<environment>[^.]+)\.de/(?P<parent_slug>[^/]+)/(?P<slug>[^/?#&]+)')
        m = content_regex.search(url)
        if m is not None:
            environment, parent_slug, slug = m.groups()
            s = requests.session()
            headers_for_origin = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0'}
            r = s.get(url=url,
                      headers=headers_for_origin)
            r.raise_for_status()

            cached_base = _do_cached_post(s=s,
                                               referer=url,
                                               url='https://de-api.loma-cms.com/feloma/configurations/?environment={0}'.format(environment))

            site_info = cached_base.get('data').get('settings').get('site')
            player_info = site_info.get('player')

            sonic_realm = player_info['sonicRealm']
            sonic_endpoint = compat_urlparse.urlparse(player_info['sonicEndpoint']).hostname
            country = site_info['info']['country']

            cached_video_specific = _do_cached_post(s=s, referer=url,
                                                         url=_generate_video_specific_cache_url(
                                                             slug=slug,
                                                             parent_slug=parent_slug))

            video_id = cached_video_specific['data']['blocks'][1]['videoId']

            try:
                return self._get_disco_api_info(url=url,
                                                display_id=video_id,
                                                disco_host=sonic_endpoint,
                                                realm=sonic_realm,
                                                country=country,
                                                api_version=3,
                                                )
            except ExtractorError as e:
                if getattr(e, 'message', '') == 'Missing deviceId in context':
                    self.report_drm(video_id)
                raise
