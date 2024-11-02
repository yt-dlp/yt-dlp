from .common import InfoExtractor
from ..utils import extract_attributes, get_element_html_by_class, remove_start


class VTVGoIE(InfoExtractor):
    _VALID_URL = [
        r'https?://(?:www\.)?vtvgo\.vn/(kho-video|tin-tuc)/[\w.-]*?(?P<id>\d+)(?:\.[a-z]+|/)?(?:$|[?#])',
        r'https?://(?:www\.)?vtvgo\.vn/digital/detail\.php\?(?:[^#]+&)?content_id=(?P<id>\d+)',
    ]
    _TESTS = [{
        'url': 'https://vtvgo.vn/kho-video/bep-vtv-vit-chao-rieng-so-24-888456.html',
        'info_dict': {
            'id': '888456',
            'ext': 'mp4',
            'title': 'Bếp VTV | Vịt chao riềng | Số 24',
            'description': 'md5:2b4e93ec2b954304170d32be288ce2c8',
            'thumbnail': 'https://vtvgo-images.vtvdigital.vn/images/20230201/VIT-CHAO-RIENG_VTV_638108894672812459.jpg',
        },
    }, {
        'url': 'https://vtvgo.vn/tin-tuc/hot-search-1-zlife-khong-ngo-toi-phai-khong-862074',
        'info_dict': {
            'id': '862074',
            'ext': 'mp4',
            'title': 'Hot Search #1 | Zlife | Không ngờ tới phải không? ',
            'description': 'md5:e967d0e2efbbebbee8814a55799b4d0f',
            'thumbnail': 'https://vtvgo-images.vtvdigital.vn/images/20220504/6b9a8552-e71c-46ce-bc9d-50c9bb506f9c.jpeg',
        },
    }, {
        'url': 'https://vtvgo.vn/kho-video/918311.html',
        'info_dict': {
            'id': '918311',
            'title': 'Cà phê sáng | 05/02/2024 | Tái hiện hình ảnh Hà Nội xưa tại ngôi nhà di sản',
            'ext': 'mp4',
            'thumbnail': 'https://vtvgo-images.vtvdigital.vn/images/20240205/0506_ca_phe_sang_638427226021318322.jpg',
            'description': 'md5:b121c67948f1ce58e6a036042fc14c1b',
        },
    }, {
        'url': 'https://vtvgo.vn/digital/detail.php?digital_id=168&content_id=918634',
        'info_dict': {
            'id': '918634',
            'ext': 'mp4',
            'title': 'Gặp nhau cuối năm | Táo quân 2024',
            'description': 'md5:a1c221e78e5954d29d49b2a11c20513c',
            'thumbnail': 'https://vtvgo-images.vtvdigital.vn/images/20240210/d0f73369-8f03-4108-9edd-83d4bc3997b2.png',
        },
    }, {
        'url': 'https://vtvgo.vn/digital/detail.php?content_id=919358',
        'info_dict': {
            'id': '919358',
            'ext': 'mp4',
            'title': 'Chúng ta của 8 năm sau | Tập 45 | Dương có bằng chứng, nhân chứng vạch mặt ông Khiêm',
            'description': 'md5:16ff5208cac6585137f554472a4677f3',
            'thumbnail': 'https://vtvgo-images.vtvdigital.vn/images/20240221/550deff9-7736-4a0e-8b5d-33274d97cd7d.jpg',
        },
    }, {
        'url': 'https://vtvgo.vn/kho-video/888456',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        m3u8_url = self._search_regex(
            r'(?:var\s+link\s*=\s*|addPlayer\()["\'](https://[^"\']+/index\.m3u8)["\']', webpage, 'm3u8 url')
        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
        }


class VTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vtv\.vn/video/[\w-]*?(?P<id>\d+)\.htm'
    _TESTS = [{
        'url': 'https://vtv.vn/video/thoi-su-20h-vtv1-12-6-2024-680411.htm',
        'info_dict': {
            'id': '680411',
            'ext': 'mp4',
            'title': 'Thời sự 20h VTV1 - 12/6/2024 - Video đã phát trên VTV1 | VTV.VN',
            'thumbnail': 'https://cdn-images.vtv.vn/zoom/600_315/66349b6076cb4dee98746cf1/2024/06/12/thumb/1206-ts-20h-02929741475480320806760.mp4/thumb0.jpg',
        },
    }, {
        'url': 'https://vtv.vn/video/zlife-1-khong-ngo-toi-phai-khong-vtv24-560248.htm',
        'info_dict': {
            'id': '560248',
            'ext': 'mp4',
            'title': 'ZLife #1: Không ngờ tới phải không? | VTV24 - Video đã phát trên VTV-NEWS | VTV.VN',
            'description': 'Ai đứng sau vụ việc thay đổi ảnh đại diện trên các trang mạng xã hội của VTV Digital tối 2/5?',
            'thumbnail': 'https://video-thumbs.mediacdn.vn/zoom/600_315/vtv/2022/5/13/t67s6btf3ji-16524555726231894427334.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data_vid = extract_attributes(get_element_html_by_class(
            'VCSortableInPreviewMode', get_element_html_by_class(
                'video-highlight-box', webpage)))['data-vid']
        m3u8_url = f'https://cdn-videos.vtv.vn/{remove_start(data_vid, "vtv.mediacdn.vn/")}/master.m3u8'
        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
        }
