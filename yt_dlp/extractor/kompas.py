from .jixie import JixieBaseIE


class KompasVideoIE(JixieBaseIE):
    _VALID_URL = r'https?://video\.kompas\.com/\w+/(?P<id>\d+)/(?P<slug>[\w-]+)'
    _TESTS = [{
        'url': 'https://video.kompas.com/watch/164474/kim-jong-un-siap-kirim-nuklir-lawan-as-dan-korsel',
        'info_dict': {
            'id': '164474',
            'ext': 'mp4',
            'title': 'Kim Jong Un Siap Kirim Nuklir Lawan AS dan Korsel',
            'description': 'md5:262530c4fb7462398235f9a5dba92456',
            'uploader_id': '9262bf2590d558736cac4fff7978fcb1',
            'display_id': 'kim-jong-un-siap-kirim-nuklir-lawan-as-dan-korsel',
            'duration': 85.066667,
            'categories': ['news'],
            'thumbnail': 'https://video.jixie.media/1001/164474/164474_1280x720.jpg',
            'tags': 'count:9',
        }
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'slug')
        webpage = self._download_webpage(url, display_id)

        return self._extract_data_from_jixie_id(display_id, video_id, webpage)
