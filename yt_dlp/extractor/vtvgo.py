from urllib.parse import urlparse

from .common import InfoExtractor


class VTVgoVideoIE(InfoExtractor):
    _VALID_URL = [
        r'(?:https://)?(?:www\.)?vtvgo\.vn/(kho-video|tin-tuc)/(?P<id>.*)\.html',
        r'(?:https://)?(?:www\.)?vtvgo\.vn/digital/detail\.php\?(?:digital_id=\d+&)?content_id=(?P<id>\d+)',
    ]
    _TESTS = [
        {
            'url': 'https://vtvgo.vn/kho-video/bep-vtv-vit-chao-rieng-so-24-888456.html',
            'info_dict': {
                'id': 'bep-vtv-vit-chao-rieng-so-24-888456',
                'ext': 'mp4',
                'title': 'Bếp VTV | Vịt chao riềng | Số 24',
                'description': 'md5:2b4e93ec2b954304170d32be288ce2c8',
                'thumbnail': 'https://vtvgo-images.vtvdigital.vn/images/20230201/VIT-CHAO-RIENG_VTV_638108894672812459.jpg',
            },
        },
        {
            'url': 'https://vtvgo.vn/tin-tuc/hot-search-1-zlife-khong-ngo-toi-phai-khong-862074.html',
            'info_dict': {
                'id': 'hot-search-1-zlife-khong-ngo-toi-phai-khong-862074',
                'ext': 'mp4',
                'title': 'Hot Search #1 | Zlife | Không ngờ tới phải không?',
                'description': 'md5:e967d0e2efbbebbee8814a55799b4d0f',
                'thumbnail': 'https://vtvgo-images.vtvdigital.vn/images/20220504/6b9a8552-e71c-46ce-bc9d-50c9bb506f9c.jpeg',
            },
        },
        {
            'url': 'https://vtvgo.vn/kho-video/ca-phe-sang-05022024-tai-hien-hinh-anh-ha-noi-xua-tai-ngoi-nha-di-san-918311.html',
            'info_dict': {
                'id': 'ca-phe-sang-05022024-tai-hien-hinh-anh-ha-noi-xua-tai-ngoi-nha-di-san-918311',
                'title': 'Cà phê sáng | 05/02/2024 | Tái hiện hình ảnh Hà Nội xưa tại ngôi nhà di sản',
                'ext': 'mp4',
                'thumbnail': 'https://vtvgo-images.vtvdigital.vn/images/20240205/0506_ca_phe_sang_638427226021318322.jpg',
                'description': 'md5:b121c67948f1ce58e6a036042fc14c1b',
            },
        },
        {
            'url': 'https://vtvgo.vn/digital/detail.php?digital_id=168&content_id=918634',
            'info_dict': {
                'id': '918634',
                'ext': 'mp4',
                'title': 'Gặp nhau cuối năm | Táo quân 2024',
            },
        },
        {
            'url': 'https://vtvgo.vn/digital/detail.php?digital_id=163&content_id=919358',
            'info_dict': {
                'id': '919358',
                'ext': 'mp4',
                'title': 'Chúng ta của 8 năm sau | Tập 45 | Dương có bằng chứng, nhân chứng vạch mặt ông Khiêm',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        m3u8_url = self._search_regex(
            r'(https://vtvgo-vods\.vtvdigital\.vn/.*/index\.m3u8)', webpage, 'm3u8_url', fatal=False,
        )
        if not m3u8_url:
            self.raise_no_formats('no m3u8 url found', video_id=video_id)
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')
        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': formats,
        }


class VTVvnIE(InfoExtractor):
    _VALID_URL = r'(?:https://)?(?:www\.)?vtv\.vn/video/(?P<id>.+)\.htm'
    _TESTS = [
        {
            'url': 'https://vtv.vn/video/thoi-su-20h-vtv1-12-6-2024-680411.htm',
            'info_dict': {
                'id': 'thoi-su-20h-vtv1-12-6-2024-680411',
                'ext': 'mp4',
                'title': 'Thời sự 20h VTV1 - 12/6/2024 - Video đã phát trên VTV1 | VTV.VN',
                'thumbnail': 'https://cdn-images.vtv.vn/zoom/600_315/66349b6076cb4dee98746cf1/2024/06/12/thumb/1206-ts-20h-02929741475480320806760.mp4/thumb0.jpg',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data_vid = self._html_search_regex(r'(\"vtv\.mediacdn\.vn/.+\.mp4\")', webpage, 'data-vid', group=1)
        parsed = urlparse(f'https://{data_vid[1:][:-1]}')  # type: ignore
        m3u8_url = f'https://cdn-videos.vtv.vn/{parsed.path}/master.m3u8'
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')
        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': formats,
        }
