from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    get_elements_html_by_class,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class GBNewsIE(InfoExtractor):
    IE_DESC = 'GB News clips, features and live streams'
    _VALID_URL = r'https?://(?:www\.)?gbnews\.(?:uk|com)/(?:\w+/)?(?P<id>[^#?]+)'

    _PLATFORM = 'safari'
    _SSMP_URL = 'https://mm-v2.simplestream.com/ssmp/api.php'
    _TESTS = [{
        'url': 'https://www.gbnews.com/news/bbc-claudine-gay-harvard-university-antisemitism-row',
        'info_dict': {
            'id': '52264136',
            'ext': 'mp4',
            'thumbnail': r're:https?://www\.gbnews\.\w+/.+\.(?:jpe?g|png|webp)',
            'display_id': 'bbc-claudine-gay-harvard-university-antisemitism-row',
            'description': 'The post was criticised by former employers of the broadcaster',
            'title': 'BBC deletes post after furious backlash over headline downplaying antisemitism',
        },
    }, {
        'url': 'https://www.gbnews.com/royal/prince-harry-in-love-with-kate-meghan-markle-jealous-royal',
        'info_dict': {
            'id': '52328390',
            'ext': 'mp4',
            'thumbnail': r're:https?://www\.gbnews\.\w+/.+\.(?:jpe?g|png|webp)',
            'display_id': 'prince-harry-in-love-with-kate-meghan-markle-jealous-royal',
            'description': 'Ingrid Seward has published 17 books documenting the highs and lows of the Royal Family',
            'title': 'Royal author claims Prince Harry was \'in love\' with Kate - Meghan was \'jealous\'',
        },
    }, {
        'url': 'https://www.gbnews.uk/watchlive',
        'info_dict': {
            'id': '1069',
            'ext': 'mp4',
            'thumbnail': r're:https?://www\.gbnews\.\w+/.+\.(?:jpe?g|png|webp)',
            'display_id': 'watchlive',
            'live_status': 'is_live',
            'title': r're:^GB News Live',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _SS_ENDPOINTS = None

    def _get_ss_endpoint(self, data_id, data_env):
        if not self._SS_ENDPOINTS:
            self._SS_ENDPOINTS = {}

        if not data_id:
            data_id = 'GB003'
        if not data_env:
            data_env = 'production'
        key = data_id, data_env
        result = self._SS_ENDPOINTS.get(key)
        if result:
            return result

        json_data = self._download_json(
            self._SSMP_URL, None, 'Downloading Simplestream JSON metadata', query={
                'id': data_id,
                'env': data_env,
            })
        meta_url = traverse_obj(json_data, ('response', 'api_hostname', {url_or_none}))
        if not meta_url:
            raise ExtractorError('No API host found')

        self._SS_ENDPOINTS[key] = meta_url
        return meta_url

    def _real_extract(self, url):
        display_id = self._match_id(url).rpartition('/')[2]
        webpage = self._download_webpage(url, display_id)

        video_data = None
        elements = get_elements_html_by_class('simplestream', webpage)
        for html_tag in elements:
            attributes = extract_attributes(html_tag)
            if 'sidebar' not in (attributes.get('class') or ''):
                video_data = attributes
        if not video_data:
            raise ExtractorError('Could not find video element', expected=True)

        endpoint_url = self._get_ss_endpoint(video_data.get('data-id'), video_data.get('data-env'))

        uvid = video_data['data-uvid']
        video_type = video_data.get('data-type')
        if not video_type or video_type == 'vod':
            video_type = 'show'
        stream_data = self._download_json(
            f'{endpoint_url}/api/{video_type}/stream/{uvid}',
            uvid, 'Downloading stream JSON', query={
                'key': video_data.get('data-key'),
                'platform': self._PLATFORM,
            })
        if traverse_obj(stream_data, 'drm'):
            self.report_drm(uvid)

        return {
            'id': uvid,
            'display_id': display_id,
            'title': self._og_search_title(webpage, default=None),
            'description': self._og_search_description(webpage, default=None),
            'formats': self._extract_m3u8_formats(traverse_obj(stream_data, (
                'response', 'stream', {url_or_none})), uvid, 'mp4'),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'is_live': video_type == 'live',
        }
