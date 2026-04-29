from .jixie import JixieBaseIE


class MoviewPlayIE(JixieBaseIE):
    _VALID_URL = r'https?://www\.moview\.id/play/\d+/(?P<id>[\w-]+)'
    _TESTS = [
        {
            # drm hls, only use direct link
            'url': 'https://www.moview.id/play/174/Candy-Monster',
            'info_dict': {
                'id': '146182',
                'ext': 'mp4',
                'display_id': 'Candy-Monster',
                'uploader_id': 'Mo165qXUUf',
                'duration': 528.2,
                'title': 'Candy Monster',
                'description': 'Mengapa Candy Monster ingin mengambil permen Chloe?',
                'thumbnail': 'https://video.jixie.media/1034/146182/146182_1280x720.jpg',
            },
        }, {
            # non-drm hls
            'url': 'https://www.moview.id/play/75/Paris-Van-Java-Episode-16',
            'info_dict': {
                'id': '28210',
                'ext': 'mp4',
                'duration': 2595.666667,
                'display_id': 'Paris-Van-Java-Episode-16',
                'uploader_id': 'Mo165qXUUf',
                'thumbnail': 'https://video.jixie.media/1003/28210/28210_1280x720.jpg',
                'description': 'md5:2a5e18d98eef9b39d7895029cac96c63',
                'title': 'Paris Van Java Episode 16',
            },
        },
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_id = self._search_regex(
            r'video_id\s*=\s*"(?P<video_id>[^"]+)', webpage, 'video_id')

        return self._extract_data_from_jixie_id(display_id, video_id, webpage)
