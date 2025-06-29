from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    url_or_none,
)
from ..utils.traversal import (
    find_element,
    require,
    traverse_obj,
)


class TheHighWireIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?thehighwire\.com/ark-videos/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://thehighwire.com/ark-videos/the-deposition-of-stanley-plotkin/',
        'info_dict': {
            'id': 'the-deposition-of-stanley-plotkin',
            'ext': 'mp4',
            'title': 'THE DEPOSITION OF STANLEY PLOTKIN',
            'description': 'md5:6d0be4f1181daaa10430fd8b945a5e54',
            'thumbnail': r're:https?://static\.arkengine\.com/video/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        embed_url = traverse_obj(webpage, (
            {find_element(cls='ark-video-embed', html=True)},
            {extract_attributes}, 'src', {url_or_none}, {require('embed URL')}))
        embed_page = self._download_webpage(embed_url, display_id)

        return {
            'id': display_id,
            **traverse_obj(webpage, {
                'title': ({find_element(cls='section-header')}, {clean_html}),
                'description': ({find_element(cls='episode-description__copy')}, {clean_html}),
            }),
            **self._parse_html5_media_entries(embed_url, embed_page, display_id, m3u8_id='hls')[0],
        }
