import logging

from .common import InfoExtractor
from ..utils import extract_attributes, get_element_by_attribute, get_element_text_and_html_by_tag

logger = logging.getLogger(__name__)


class HEINetworkTVVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?heinetwork\.tv/(?P<series>[\w-]+)/(?P<season>[\w-]+)/(?P<id>[\w-]+)'
    _TESTS = [{
        # requires cookies
        'url': 'https://www.heinetwork.tv/on-cinema-at-the-cinema/season-2/side-effects-and-identity-thief/',
        'md5': 'd10a28af64c3c34a69baa3f38a8c760b',
        'info_dict': {
            'id': 'side-effects-and-identity-thief',
            'title': '201 ‘Side Effects’ and ‘Identity Thief’',
            'ext': 'mp4',
        },
    }]

    def _is_logged_in(self, webpage):
        return get_element_by_attribute('href', '/my-account', webpage) is not None

    def _extract_video_src(self, webpage):
        _, html = get_element_text_and_html_by_tag('castable-video', webpage)
        attrs = extract_attributes(html)
        return attrs['src']

    def _extract_video_title(self, webpage):
        _, mux_video = get_element_text_and_html_by_tag('mux-video', webpage)
        attrs = extract_attributes(mux_video)
        if 'metadata-video-title' not in attrs:
            return None
        return attrs['metadata-video-title']

    def _real_extract(self, url):
        if not self._is_logged_in(self._download_webpage('https://www.heinetwork.tv/', None)):
            logger.warning('You are not logged in. Some videos may be unavailable.')

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_src = self._extract_video_src(webpage)
        formats, _subs = self._extract_m3u8_formats_and_subtitles(video_src, video_id)

        return {
            'id': video_id,
            'title': self._extract_video_title(webpage),
            'formats': formats,
        }
