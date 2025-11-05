from .common import InfoExtractor


class MuxStreamNewIE(InfoExtractor):
    IE_NAME = 'stream.new'
    _WORKING = True
    _VALID_URL = r'https?://stream.new/v/(?P<id>[A-Za-z0-9-]+)(/embed)?'
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

        video_url = 'https://stream.mux.com/%s.m3u8' % video_id

        formats = self._extract_m3u8_formats(
            video_url, video_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
            '_type': 'video',
        }
