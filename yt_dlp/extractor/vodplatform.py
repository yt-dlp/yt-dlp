from .common import InfoExtractor
from ..utils import unescapeHTML


class VODPlatformIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?vod-platform\.net|embed\.kwikmotion\.com)/[eE]mbed/(?P<id>[^/?#]+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:(?:www\.)?vod-platform\.net|embed\.kwikmotion\.com)/[eE]mbed/.+?)\1']
    _TESTS = [{
        # from http://www.lbcgroup.tv/watch/chapter/29143/52844/%D8%A7%D9%84%D9%86%D8%B5%D8%B1%D8%A9-%D9%81%D9%8A-%D8%B6%D9%8A%D8%A7%D9%81%D8%A9-%D8%A7%D9%84%D9%80-cnn/ar
        'url': 'http://vod-platform.net/embed/RufMcytHDolTH1MuKHY9Fw',
        'md5': '1db2b7249ce383d6be96499006e951fc',
        'info_dict': {
            'id': 'RufMcytHDolTH1MuKHY9Fw',
            'ext': 'mp4',
            'title': 'LBCi News_ النصرة في ضيافة الـ "سي.أن.أن"',
        }
    }, {
        'url': 'http://embed.kwikmotion.com/embed/RufMcytHDolTH1MuKHY9Fw',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = unescapeHTML(self._og_search_title(webpage))
        hidden_inputs = self._hidden_inputs(webpage)

        formats = self._extract_wowza_formats(
            hidden_inputs.get('HiddenmyhHlsLink') or hidden_inputs['HiddenmyDashLink'], video_id, skip_protocols=['f4m', 'smil'])

        return {
            'id': video_id,
            'title': title,
            'thumbnail': hidden_inputs.get('HiddenThumbnail') or self._og_search_thumbnail(webpage),
            'formats': formats,
        }
