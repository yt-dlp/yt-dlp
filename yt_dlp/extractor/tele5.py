import re
import requests

from traceback import format_exception

from .dplay import DPlayIE
from ..compat import compat_urlparse
from ..utils import (
    ExtractorError, get_default_user_agent,
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
                   'Referer': referer,
                   'User-Agent': get_default_user_agent(),
               },
               json={'path': url}
               )
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise ExtractorError("Post to Loma-CMS failed {0}".format(format_exception(e)))
    return r.json()


class Tele5IE(DPlayIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?://(?:www\.)?tele5\.de/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _GEO_COUNTRIES = ['DE']
    _TESTS = [{
        'url': 'https://tele5.de/mediathek/schlefaz',
        'info_dict': {
            'id': '61b09a6bb0ed8d9799911e98',
            'title': 'SchleFaZ',
        },
        'playlist_mincount': 4,
    }, {
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
        'url': 'https://tele5.de/mediathek/giganten-mit-staehlernen-faeusten',
        'info_dict': {
            'id': '5561439',
            'title': 'Giganten mit stählernen Fäusten',
            'ext': 'mp4',
            'timestamp': 1697235900,
            'description': 'md5:80489c885ae763b0f7fb74c65bbbdbde',
            'creator': 'Tele5',
            'tags': [],
            'series': 'Giganten mit stählernen Fäusten',
            'duration': 4690.68,
            'upload_date': '20231013',
            'thumbnail': 'https://eu1-prod-images.disco-api.com/2023/09/28/274524f7-e71d-334b-9971-c0c439eca577.jpeg',
        },
    }, {
        'url': 'https://tele5.de/mediathek/ein-koenigreich-vor-unserer-zeit',
        'info_dict': {
            'id': '5467119',
            'ext': 'mp4',
            'duration': 4506.6,
            'description': 'md5:7670c325232d54cb1fb0e1cb91770431',
            'creator': 'Tele5',
            'title': 'Ein Königreich vor unserer Zeit',
            'timestamp': 1695422100,
            'tags': [],
            'series': 'Ein Königreich vor unserer Zeit',
            'upload_date': '20230922',
            'thumbnail': 'https://eu1-prod-images.disco-api.com/2023/09/13/4fb0ad33-9644-3c9b-8e5e-71db184e029e.jpeg',
        },
    }, {
        'url': 'https://tele5.de/mediathek/im-reich-der-amazonen',
        'info_dict': {
            'id': '5503913',
            'ext': 'mp4',
            'series': 'Im Reich der Amazonen',
            'duration': 4811.76,
            'creator': 'Tele5',
            'description': 'md5:fb4a571d008806eb09f4818e2240a106',
            'thumbnail': 'https://eu1-prod-images.disco-api.com/2023/09/18/df0205cd-9dd8-3368-a31b-7f9c28f99021.jpeg',
            'timestamp': 1696025700,
            'title': 'Im Reich der Amazonen',
            'tags': [],
            'upload_date': '20230929',
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
        content_regex = re.compile(
            r'https?://(?:www\.)?(?P<environment>[^.]+)\.de/(?P<parent_slug>[^/]+)/(?P<slug>[^/?#&]+)')
        m = content_regex.search(url)
        if m is None:
            raise ExtractorError('Could not parse url {0} to environment, parent_slug, slug'.format(url))
        else:
            environment, parent_slug, slug = m.groups()
            s = requests.session()
            headers_for_origin = {
                'User-Agent': get_default_user_agent()}
            r = s.get(url=url,
                      headers=headers_for_origin)
            r.raise_for_status()

            cached_base = _do_cached_post(
                s=s,
                referer=url,
                url='https://de-api.loma-cms.com/feloma/configurations/?environment={0}'.format(environment))

            cached_video_specific = _do_cached_post(s=s,
                                                    referer=url,
                                                    url=_generate_video_specific_cache_url(
                                                        slug=slug,
                                                        parent_slug=parent_slug))

            try:
                site_info = cached_base['data']['settings']['site']
                country = site_info['info']['country']
                player_info = site_info['player']
                sonic_realm = player_info['sonicRealm']
                sonic_endpoint = compat_urlparse.urlparse(player_info['sonicEndpoint']).hostname

                video_ids = [block['videoId'] for block in cached_video_specific['data']['blocks'] if
                             block['type'] == 'sonicVideoBlock']
                assert len(video_ids) > 0
            except (KeyError, TypeError, AssertionError):
                raise ExtractorError('Could not extract Meta Data from loma-cms')

            entries = []
            for video_id in video_ids:
                try:
                    video_info = self._get_disco_api_info(url=url,
                                                          display_id=video_id,
                                                          disco_host=sonic_endpoint,
                                                          realm=sonic_realm,
                                                          country=country,
                                                          api_version=3,
                                                          )
                    entries.append(video_info)
                except ExtractorError as e:
                    if getattr(e, 'message', '') == 'Missing deviceId in context':
                        self.report_drm(video_id)
                    raise

            if len(video_ids) == 1:
                return entries[0]
            else:
                return {'_type': 'playlist',
                        'id': cached_video_specific['data']['uid'],
                        'title': cached_video_specific['data']['title'],
                        'entries': entries}
