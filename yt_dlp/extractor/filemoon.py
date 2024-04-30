from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import parse_codecs

class FileMoonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?filemoon\.sx/./(?P<id>\w+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        matches = self._parse_html(webpage, video_id)
        jwplayer_sources = matches.get('jwplayer_sources', [])

        formats = self._parse_jwplayer_formats(jwplayer_sources, video_id)

        return {
            'id': video_id,
            'title': self._generic_title(url) or video_id,
            'formats': formats
        }

    def _parse_jwplayer_formats(self, jwplayer_sources, video_id):
        formats = []
        for source in jwplayer_sources:
            format_id = '%s-%s' % (source.get('height'), source.get('container'))
            codecs = parse_codecs(source.get('type'))
            format_info = {
                'format_id': format_id,
                'url': source['file'],
                'ext': source.get('container'),
                'vcodec': codecs.get('vcodec'),
                'acodec': codecs.get('acodec'),
                'width': source.get('width'),
                'height': source.get('height'),
                'filesize': source.get('size'),
                'protocol': source.get('protocol'),
                'http_headers': source.get('http_headers'),
            }
            formats.append(format_info)
        return formats
