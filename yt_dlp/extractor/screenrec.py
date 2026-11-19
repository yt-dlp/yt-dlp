from .common import InfoExtractor
from ..utils import js_to_json, unified_strdate
from ..utils.traversal import require, traverse_obj


class ScreenRecIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?screenrec\.com/share/(?P<id>\w{10})'
    _TESTS = [{
        # live_id
        'url': 'https://screenrec.com/share/lkmH0Zu5gM',
        'info_dict': {
            'id': 'lkmH0Zu5gM',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.(?:png|jpg)',
            'upload_date': '20261119',
            'description': 'md5:110a66bcea744bf0d6dbca3a0b9419f8',
            'title': 'Settings Panel Overview Tour',
        },
    }, {
        # live_id
        'url': 'https://screenrec.com/share/deMq9rFaZz',
        'info_dict': {
            'id': 'deMq9rFaZz',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.(?:png|jpg)',
            'upload_date': '20261119',
            'description': 'md5:c0d339e767e0dc90b330e4f6dc42b6f9',
            'title': 'Quick Tour of Analytics Panel',
        },
    }, {
        # clip_id
        'url': 'https://screenrec.com/share/ZHwdTfY23O',
        'info_dict': {
            'id': 'ZHwdTfY23O',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.gif',
            'upload_date': '20261117',
            'title': '17.11.2026_12.01.13_REC',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        clip_id = traverse_obj(
            self._search_json(
                r'var\s+vars\s*=', webpage, 'player vars',
                video_id, transform_source=js_to_json, fatal=False),
            ('clip_id', {str}))
        if not clip_id:
            clip_id = self._search_json(
                r'var\s+params\s*=', webpage, 'player params',
                video_id, transform_source=js_to_json)['live_id']

        info_xml = self._download_xml(
            'https://service.webvideocore.net/', video_id, query={
                'l': 'info',
                'a': 'xmlClipPath',
                'page_url': url,
                'clip_id': clip_id,
                'version': '5',
                'preview': '0',
                'timezone_offset': '0',
                'init': 'true',
            })

        m3u8_url = traverse_obj(info_xml, ('info/url/text()', ..., any, {require('m3u8 URL')}))
        metadata = traverse_obj(info_xml, ('info/meta', ..., any))

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id),
            'thumbnail': traverse_obj(metadata, ('clip_image/text()', ..., any)) or self._og_search_thumbnail(webpage),
            **traverse_obj(metadata, {
                'upload_date': ('clip_date_created/text()', ..., {unified_strdate}, any),
                'description': (('clip_long_descr/text()', 'clip_descr/text()'), ..., any),
                'title': ('clip_title/text()', ..., any),
            }),
        }
