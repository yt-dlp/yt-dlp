import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_attribute,
    get_elements_html_by_class,
    int_or_none,
    parse_duration,
    parse_iso8601,
    remove_start,
    str_or_none,
    strip_or_none,
    unescapeHTML,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class Kenh14VideoIE(InfoExtractor):
    _VALID_URL = r'https?://video\.kenh14\.vn/(?:video/)?[\w-]+-(?P<id>[0-9]+)\.chn'
    _TESTS = [{
        'url': 'https://video.kenh14.vn/video/mo-hop-iphone-14-pro-max-nguon-unbox-therapy-316173.chn',
        'md5': '1ed67f9c3a1e74acf15db69590cf6210',
        'info_dict': {
            'id': '316173',
            'ext': 'mp4',
            'title': 'Video mở hộp iPhone 14 Pro Max (Nguồn: Unbox Therapy)',
            'description': 'Video mở hộp iPhone 14 Pro MaxVideo mở hộp iPhone 14 Pro Max (Nguồn: Unbox Therapy)',
            'thumbnail': r're:^https?://videothumbs\.mediacdn\.vn/.*\.jpg$',
            'tags': [],
            'uploader': 'Unbox Therapy',
            'upload_date': '20220517',
            'view_count': int,
            'duration': 722.86,
            'timestamp': 1652764468,
        },
    }, {
        'url': 'https://video.kenh14.vn/video-316174.chn',
        'md5': '2b41877d2afaf4a3f487ceda8e5c7cbd',
        'info_dict': {
            'id': '316174',
            'ext': 'mp4',
            'title': 'Khoảnh khắc VĐV nằm gục khóc sau chiến thắng: 7 năm trời Việt Nam mới có HCV kiếm chém nữ, chỉ có 8 tháng để khổ luyện trước khi lên sàn đấu',
            'description': 'md5:de86aa22e143e2b277bce8ec9c6f17dc',
            'thumbnail': r're:^https?://videothumbs\.mediacdn\.vn/.*\.jpg$',
            'tags': [],
            'upload_date': '20220517',
            'view_count': int,
            'duration': 70.04,
            'timestamp': 1652766021,
        },
    }, {
        'url': 'https://video.kenh14.vn/0-344740.chn',
        'md5': 'b843495d5e728142c8870c09b46df2a9',
        'info_dict': {
            'id': '344740',
            'ext': 'mov',
            'title': 'Kỳ Duyên đầy căng thẳng trong buổi ra quân đi Miss Universe, nghi thức tuyên thuệ lần đầu xuất hiện gây nhiều tranh cãi',
            'description': 'md5:2a2dbb4a7397169fb21ee68f09160497',
            'thumbnail': r're:^https?://kenh14cdn\.com/.*\.jpg$',
            'tags': ['kỳ duyên', 'Kỳ Duyên tuyên thuệ', 'miss universe'],
            'uploader': 'Quang Vũ',
            'upload_date': '20241024',
            'view_count': int,
            'duration': 198.88,
            'timestamp': 1729741590,
        },
        'expected_warnings': [
            'Failed to download m3u8 information: HTTP Error 404: NOT FOUND',
        ],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        attrs = extract_attributes(get_element_html_by_attribute('type', 'VideoStream', webpage) or '')
        direct_url = attrs['data-vid']

        metadata = self._download_json(
            'https://api.kinghub.vn/video/api/v1/detailVideoByGet?FileName={}'.format(
                remove_start(direct_url, 'kenh14cdn.com/')), video_id, fatal=False)

        return {
            'id': video_id,
            'title': (
                strip_or_none(metadata.get('title'))
                or clean_html(self._og_search_title(webpage))
                or clean_html(get_element_by_class('vdbw-title', webpage))),
            'formats': [
                {'url': f'https://{direct_url}', 'format_id': 'http'},
                *self._extract_m3u8_formats(f'https://{direct_url}/master.m3u8', video_id, fatal=False),
            ],
            'duration': parse_duration(metadata.get('duration')),
            'description': (
                clean_html(self._og_search_description(webpage))
                or clean_html(get_element_by_class('vdbw-sapo', webpage))),
            'thumbnail': (self._og_search_thumbnail(webpage) or attrs.get('data-thumb')),
            'uploader': strip_or_none(metadata.get('author')),
            'timestamp': parse_iso8601(metadata.get('uploadtime'), delimiter=' '),
            'view_count': int_or_none(metadata.get('views')),
            'tags': traverse_obj(self._html_search_meta('keywords', webpage), (
                {lambda x: x.split(';')}, lambda _, v: v, {str_or_none})),
        }


class Kenh14PlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://video\.kenh14\.vn/playlist/[\w-]+-(?P<id>[0-9]+)\.chn'
    _TESTS = [{
        'url': 'https://video.kenh14.vn/playlist/tran-tinh-naked-love-mua-2-71.chn',
        'info_dict': {
            'id': '71',
            'title': 'Trần Tình (Naked love) mùa 2',
            'description': 'md5:e9522339304956dea931722dd72eddb2',
            'thumbnail': r're:^https?://kenh14cdn\.com/.*\.png$',
        },
        'playlist_count': 9,
    }, {
        'url': 'https://video.kenh14.vn/playlist/0-72.chn',
        'info_dict': {
            'id': '72',
            'title': 'Lau Lại Đầu Từ',
            'description': 'Cùng xem xưa và nay có gì khác biệt nhé!',
            'thumbnail': r're:^https?://kenh14cdn\.com/.*\.png$',
        },
        'playlist_count': 6,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        category_detail = get_element_by_class('category-detail', webpage)
        embed_info = traverse_obj(
            self._yield_json_ld(webpage, playlist_id),
            (lambda _, v: v['name'] and v['alternateName']), get_all=False)

        return self.playlist_from_matches(
            get_elements_html_by_class('video-item', webpage), playlist_id,
            (clean_html(get_element_by_class('name', category_detail)) or unescapeHTML(embed_info.get('name'))),
            getter=lambda x: 'https://video.kenh14.vn/video/{}.chn'.format(extract_attributes(x)['data-id']),
            ie=Kenh14VideoIE.ie_key(), playlist_description=(
                clean_html(get_element_by_class('description', category_detail))
                or unescapeHTML(embed_info.get('alternateName'))),
            thumbnail=traverse_obj(
                self._og_search_thumbnail(webpage),
                ({url_or_none}, {lambda x: urllib.parse.urlunparse(urllib.parse.urlparse(x)._replace(query=None))})))
