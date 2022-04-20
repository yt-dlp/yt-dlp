import re

from .common import InfoExtractor


class OnceIE(InfoExtractor):
    _VALID_URL = r'https?://.+?\.unicornmedia\.com/now/(?:ads/vmap/)?[^/]+/[^/]+/(?P<domain_id>[^/]+)/(?P<application_id>[^/]+)/(?:[^/]+/)?(?P<media_item_id>[^/]+)/content\.(?:once|m3u8|mp4)'
    ADAPTIVE_URL_TEMPLATE = 'http://once.unicornmedia.com/now/master/playlist/%s/%s/%s/content.m3u8'
    PROGRESSIVE_URL_TEMPLATE = 'http://once.unicornmedia.com/now/media/progressive/%s/%s/%s/%s/content.mp4'

    def _extract_once_formats(self, url, http_formats_preference=None):
        domain_id, application_id, media_item_id = re.match(
            OnceIE._VALID_URL, url).groups()
        formats = self._extract_m3u8_formats(
            self.ADAPTIVE_URL_TEMPLATE % (
                domain_id, application_id, media_item_id),
            media_item_id, 'mp4', m3u8_id='hls', fatal=False)
        progressive_formats = []
        for adaptive_format in formats:
            # Prevent advertisement from embedding into m3u8 playlist (see
            # https://github.com/ytdl-org/youtube-dl/issues/8893#issuecomment-199912684)
            adaptive_format['url'] = re.sub(
                r'\badsegmentlength=\d+', r'adsegmentlength=0', adaptive_format['url'])
            rendition_id = self._search_regex(
                r'/now/media/playlist/[^/]+/[^/]+/([^/]+)',
                adaptive_format['url'], 'redition id', default=None)
            if rendition_id:
                progressive_format = adaptive_format.copy()
                progressive_format.update({
                    'url': self.PROGRESSIVE_URL_TEMPLATE % (
                        domain_id, application_id, rendition_id, media_item_id),
                    'format_id': adaptive_format['format_id'].replace(
                        'hls', 'http'),
                    'protocol': 'http',
                    'preference': http_formats_preference,
                })
                progressive_formats.append(progressive_format)
        self._check_formats(progressive_formats, media_item_id)
        formats.extend(progressive_formats)
        return formats
