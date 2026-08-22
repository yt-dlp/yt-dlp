from .common import InfoExtractor


class StreamffIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamff\.com/v/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://streamff.com/v/74341c35',
        'md5': 'afbdb74dc6e53477b1f1083793cfc2df',
        'info_dict': {
            'id': '74341c35',
            'ext': 'mp4',
            'title': '74341c35',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        return {
            'id': video_id,
            'title': video_id,
            'url': f'https://ffedge.streamff.com/uploads/{video_id}.mp4',
        }
