from .brightcove import BrightcoveNewIE
from ..utils import extract_attributes


class BandaiChannelIE(BrightcoveNewIE):
    IE_NAME = 'bandaichannel'
    _VALID_URL = r'https?://(?:www\.)?b-ch\.com/titles/(?P<id>\d+/\d+)'
    _TESTS = [{
        'url': 'https://www.b-ch.com/titles/514/001',
        'md5': 'a0f2d787baa5729bed71108257f613a4',
        'info_dict': {
            'id': '6128044564001',
            'ext': 'mp4',
            'title': 'メタルファイターMIKU 第1話',
            'timestamp': 1580354056,
            'uploader_id': '5797077852001',
            'upload_date': '20200130',
            'duration': 1387.733,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        attrs = extract_attributes(self._search_regex(
            r'(<video-js[^>]+\bid="bcplayer"[^>]*>)', webpage, 'player'))
        bc = self._download_json(
            'https://pbifcd.b-ch.com/v1/playbackinfo/ST/70/' + attrs['data-info'],
            video_id, headers={'X-API-KEY': attrs['data-auth'].strip()})['bc']
        return self._parse_brightcove_metadata(bc, bc['id'])
