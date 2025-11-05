from .common import InfoExtractor


class MuxStreamNewIE(InfoExtractor):
    IE_NAME = 'stream.new'
    _VALID_URL = r'https?://(?:stream\.new/v|player\.mux\.com)/(?P<id>[A-Za-z0-9-]+)'
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=["\'](?P<url>(?:https?:)?//(?:stream\.new/v|player\.mux\.com)/(?P<id>[A-Za-z0-9-]+))']
    _TESTS = [{
        'url': 'https://stream.new/v/36d8c00L1vEFwF01aF1cRKQs8nblgegMda8YR9CE3wejk/embed',
        'info_dict': {
            'id': '36d8c00L1vEFwF01aF1cRKQs8nblgegMda8YR9CE3wejk',
            'title': '36d8c00L1vEFwF01aF1cRKQs8nblgegMda8YR9CE3wejk',
            'formats': 'mincount:1',
            'ext': 'mp4',
            '_type': 'video',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        formats = self._extract_m3u8_formats(
            f'https://stream.mux.com/{video_id}.m3u8', video_id, 'mp4')

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }
