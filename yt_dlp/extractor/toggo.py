import urllib.parse
from copy import copy

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import int_or_none


class ToggoIE(InfoExtractor):
    IE_NAME = 'toggo'
    _VALID_URL = r'https?://(?:www\.)?toggo\.de/[\w-]+/folge/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.toggo.de/weihnachtsmann--co-kg/folge/ein-geschenk-fuer-zwei',
        'md5': 'fb55764928baa57d4b0eb03441b50804',
        'info_dict': {
            'id': 'VEP2977',
            'ext': 'ism',
            'title': 'Ein Geschenk für zwei',
            'language': 'en',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'description': 'md5:b7715915bfa47824b4e4ad33fb5962f8',
            'release_timestamp': 1637259179,
            'series': 'Weihnachtsmann & Co. KG',
            'season': 'Weihnachtsmann & Co. KG',
            'season_number': 1,
            'season_id': 'VST118',
            'episode': 'Ein Geschenk für zwei',
            'episode_number': 7,
            'episode_id': 'VEP2977',
            'timestamp': 1581935960,
            'uploader_id': '6057955896001',
            'upload_date': '20200217',
        }
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)

        data = self._download_json(
            f'https://production-n.toggo.de/api/assetstore/vod/asset/{slug}', slug)['data']

        video_id = next(
            x['value'] for x in data['custom_fields'] if x['key'] == 'video-cloud-id')

        brightcove_ie = BrightcoveNewIE()
        downloader = copy(self._downloader)
        # This is needed to ignore the DRM error because we're going to replace the fragment base URL later on
        downloader.params = {'allow_unplayable_formats': True}
        brightcove_ie.set_downloader(downloader)

        info = brightcove_ie._real_extract(
            f'http://players.brightcove.net/6057955896001/default_default/index.html?videoId={video_id}')

        thumbnails = []
        for thumb in (data.get('images') or {}).values():
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(thumb).query)
            thumbnails.append({
                'url': thumb,
                'width': int_or_none(next(iter(qs['width']), None)),
            })

        info.update({
            'id': data.get('id'),
            'title': data.get('title'),
            'language': data.get('language'),
            'thumbnails': thumbnails,
            'description': data.get('description'),
            'release_timestamp': data.get('earliest_start_date'),
            'series': data.get('series_title'),
            'season': data.get('season_title'),
            'season_number': data.get('season_no'),
            'season_id': data.get('season_id'),
            'episode': data.get('title'),
            'episode_number': data.get('episode_no'),
            'episode_id': data.get('id'),
        })

        for f in info['formats']:
            if '/dash/live/cenc/' in f.get('fragment_base_url', ''):
                # Get hidden non-DRM format
                f['fragment_base_url'] = f['fragment_base_url'].replace('/cenc/', '/clear/')
                f['has_drm'] = False

            if '/fairplay/' in f.get('manifest_url', ''):
                f['has_drm'] = True

        return info
