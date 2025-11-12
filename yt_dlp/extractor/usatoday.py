from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    get_element_by_attribute,
    parse_duration,
    try_get,
    update_url_query,
)


class USATodayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?usatoday\.com/(?:[^/]+/)*(?P<id>[^?/#]+)'
    _TESTS = [{
        # Brightcove Partner ID = 29906170001
        'url': 'http://www.usatoday.com/media/cinematic/video/81729424/us-france-warn-syrian-regime-ahead-of-new-peace-talks/',
        'md5': '033587d2529dc3411a1ab3644c3b8827',
        'info_dict': {
            'id': '4799374959001',
            'ext': 'mp4',
            'title': 'US, France warn Syrian regime ahead of new peace talks',
            'timestamp': 1457891045,
            'description': 'md5:7e50464fdf2126b0f533748d3c78d58f',
            'uploader_id': '29906170001',
            'upload_date': '20160313',
        },
    }, {
        # ui-video-data[asset_metadata][items][brightcoveaccount] = 28911775001
        'url': 'https://www.usatoday.com/story/tech/science/2018/08/21/yellowstone-supervolcano-eruption-stop-worrying-its-blow/973633002/',
        'info_dict': {
            'id': '5824495846001',
            'ext': 'mp4',
            'title': 'Yellowstone more likely to crack rather than explode',
            'timestamp': 1534790612,
            'description': 'md5:3715e7927639a4f16b474e9391687c62',
            'uploader_id': '28911775001',
            'upload_date': '20180820',
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(update_url_query(url, {'ajax': 'true'}), display_id)
        ui_video_data = get_element_by_attribute('class', 'ui-video-data', webpage)
        if not ui_video_data:
            raise ExtractorError('no video on the webpage', expected=True)
        video_data = self._parse_json(ui_video_data, display_id)
        item = try_get(video_data, lambda x: x['asset_metadata']['items'], dict) or {}

        return {
            '_type': 'url_transparent',
            'url': self.BRIGHTCOVE_URL_TEMPLATE % (item.get('brightcoveaccount', '29906170001'), item.get('brightcoveid') or video_data['brightcove_id']),
            'id': str(video_data['id']),
            'title': video_data['title'],
            'thumbnail': video_data.get('thumbnail'),
            'description': video_data.get('description'),
            'duration': parse_duration(video_data.get('length')),
            'ie_key': 'BrightcoveNew',
        }
