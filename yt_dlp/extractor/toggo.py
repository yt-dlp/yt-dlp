from .common import InfoExtractor
from ..utils import int_or_none, parse_qs


class ToggoIE(InfoExtractor):
    IE_NAME = 'toggo'
    _VALID_URL = r'https?://(?:www\.)?toggo\.de/[\w-]+/folge/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.toggo.de/weihnachtsmann--co-kg/folge/ein-geschenk-fuer-zwei',
        'info_dict': {
            'id': 'VEP2977',
            'ext': 'mp4',
            'title': 'Ein Geschenk für zwei',
            'display_id': 'ein-geschenk-fuer-zwei',
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
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        data = self._download_json(
            f'https://production-n.toggo.de/api/assetstore/vod/asset/{display_id}', display_id)['data']

        brightcove_id = next(
            x['value'] for x in data['custom_fields'] if x.get('key') == 'video-cloud-id')
        info = self._downloader.get_info_extractor('BrightcoveNew').extract(
            f'http://players.brightcove.net/6057955896001/default_default/index.html?videoId={brightcove_id}')

        for f in info['formats']:
            if '/dash/live/cenc/' in f.get('fragment_base_url', ''):
                # Get hidden non-DRM format
                f['fragment_base_url'] = f['fragment_base_url'].replace('/cenc/', '/clear/')
                f['has_drm'] = False

            if '/fairplay/' in f.get('manifest_url', ''):
                f['has_drm'] = True

        thumbnails = [{
            'id': name,
            'url': url,
            'width': int_or_none(next(iter(parse_qs(url).get('width', [])), None)),
        } for name, url in (data.get('images') or {}).items()]

        return {
            **info,
            'id': data.get('id'),
            'display_id': display_id,
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
        }
