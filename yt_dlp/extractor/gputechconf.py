from .common import InfoExtractor


class GPUTechConfIE(InfoExtractor):
    _VALID_URL = r'https?://on-demand\.gputechconf\.com/gtc/2015/video/S(?P<id>\d+)\.html'
    _TEST = {
        'url': 'http://on-demand.gputechconf.com/gtc/2015/video/S5156.html',
        'md5': 'a8862a00a0fd65b8b43acc5b8e33f798',
        'info_dict': {
            'id': '5156',
            'ext': 'mp4',
            'title': 'Coordinating More Than 3 Million CUDA Threads for Social Network Analysis',
            'duration': 1219,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        root_path = self._search_regex(
            r'var\s+rootPath\s*=\s*"([^"]+)', webpage, 'root path',
            default='http://evt.dispeak.com/nvidia/events/gtc15/')
        xml_file_id = self._search_regex(
            r'var\s+xmlFileId\s*=\s*"([^"]+)', webpage, 'xml file id')

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': '%sxml/%s.xml' % (root_path, xml_file_id),
            'ie_key': 'DigitallySpeaking',
        }
