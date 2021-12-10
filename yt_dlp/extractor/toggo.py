from copy import copy

from .common import InfoExtractor
from .extractors import BrightcoveNewIE


class ToggoIE(InfoExtractor):
    IE_NAME = 'toggo'
    _VALID_URL = r'https?://(?:www\.)?toggo\.de/[\w-]+/folge/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.toggo.de/weihnachtsmann--co-kg/folge/ein-geschenk-fuer-zwei',
        'md5': 'TODO',
        'info_dict': {
            'id': '6133142945001',
            'ext': 'mp4',
            'title': 'Ein Geschenk für zwei',
            'language': 'de',
            'thumbnail': r're:^http://.*\.jpg',
            'description': '',
            'release_timestamp': 'TODO',
        }
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)

        data = self._download_json(
            f'https://production-n.toggo.de/api/assetstore/vod/asset/{slug}', slug)

        video_id = next(
            x['value'] for x in data['data']['custom_fields'] if x['key'] == 'video-cloud-id')

        brightcove_ie = BrightcoveNewIE()
        downloader = copy(self._downloader)
        # This is needed to ignore the DRM error because we're going to replace the fragment base URL later on
        downloader.params = {'allow_unplayable_formats': True}
        brightcove_ie.set_downloader(downloader)

        info = brightcove_ie._real_extract(
            f'http://players.brightcove.net/6057955896001/default_default/index.html?videoId={video_id}')
        for f in info['formats']:
            if '/dash/live-baseurl/bccenc/' in f.get('manifest_url', ''):
                # Get hidden non-DRM format
                f['fragment_base_url'] = f['fragment_base_url'].replace('/cenc/', '/clear/')
                f['has_drm'] = False
        return info
