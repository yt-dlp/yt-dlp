from .common import InfoExtractor

class TheHighWireIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?thehighwire\.com/ark-videos/(?P<id>[^/?#]+)'
    _EMBED_URL = 'https://app.arkengine.com/embed/{id}'
    _TESTS = [{
        'url': 'https://thehighwire.com/ark-videos/the-deposition-of-stanley-plotkin/',
        'info_dict': {
            'id': 'clllgcra301z4ik01x8cwhfu2',
            'title': 'THE DEPOSITION OF STANLEY PLOTKIN',
            'ext': 'mp4',
        },
        'params': {'skip_download': True},
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

