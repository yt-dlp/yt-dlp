from .common import InfoExtractor
from .jwplatform import JWPlatformIE


class BundesligaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bundesliga\.com/[a-z]{2}/bundesliga/videos\?vid=(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.bundesliga.com/en/bundesliga/videos?vid=bhhHkKyN',
        'md5': '8fc3b25cd12440e3a8cdc51f1493849c',
        'info_dict': {
            'id': 'bhhHkKyN',
            'ext': 'mp4',
            'title': 'Watch: Alphonso Davies and Jeremie Frimpong head-to-head',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/bhhHkKyN/poster.jpg?width=720',
            'upload_date': '20220928',
            'duration': 146,
            'timestamp': 1664366511,
            'description': 'md5:803d4411bd134140c774021dd4b7598b'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            f'jwplatform:{video_id}', ie=JWPlatformIE.ie_key(),
            video_id=video_id)
