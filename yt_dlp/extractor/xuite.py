from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    get_element_by_attribute,
    parse_iso8601,
    remove_end,
)


class XuiteIE(InfoExtractor):
    IE_DESC = '隨意窩Xuite影音'
    _REGEX_BASE64 = r'(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?'
    _VALID_URL = r'https?://vlog\.xuite\.net/(?:play|embed)/(?P<id>%s)' % _REGEX_BASE64
    _TESTS = [{
        # Audio
        'url': 'http://vlog.xuite.net/play/RGkzc1ZULTM4NjA5MTQuZmx2',
        'md5': 'e79284c87b371424885448d11f6398c8',
        'info_dict': {
            'id': '3860914',
            'ext': 'mp3',
            'title': '孤單南半球-歐德陽',
            'description': '孤單南半球-歐德陽',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 247.246,
            'timestamp': 1314932940,
            'upload_date': '20110902',
            'uploader': '阿能',
            'uploader_id': '15973816',
            'categories': ['個人短片'],
        },
    }, {
        # Video with only one format
        'url': 'http://vlog.xuite.net/play/WUxxR2xCLTI1OTI1MDk5LmZsdg==',
        'md5': '21f7b39c009b5a4615b4463df6eb7a46',
        'info_dict': {
            'id': '25925099',
            'ext': 'mp4',
            'title': 'BigBuckBunny_320x180',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 596.458,
            'timestamp': 1454242500,
            'upload_date': '20160131',
            'uploader': '屁姥',
            'uploader_id': '12158353',
            'categories': ['個人短片'],
            'description': 'http://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4',
        },
    }, {
        # Video with two formats
        'url': 'http://vlog.xuite.net/play/bWo1N1pLLTIxMzAxMTcwLmZsdg==',
        'md5': '1166e0f461efe55b62e26a2d2a68e6de',
        'info_dict': {
            'id': '21301170',
            'ext': 'mp4',
            'title': '暗殺教室 02',
            'description': '字幕:【極影字幕社】',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1384.907,
            'timestamp': 1421481240,
            'upload_date': '20150117',
            'uploader': '我只是想認真點',
            'uploader_id': '242127761',
            'categories': ['電玩動漫'],
        },
        'skip': 'Video removed',
    }, {
        # Video with encoded media id
        # from http://forgetfulbc.blogspot.com/2016/06/date.html
        'url': 'http://vlog.xuite.net/embed/cE1xbENoLTI3NDQ3MzM2LmZsdg==?ar=0&as=0',
        'info_dict': {
            'id': '27447336',
            'ext': 'mp4',
            'title': '男女平權只是口號？專家解釋約會時男生是否該幫女生付錢 (中字)',
            'description': 'md5:1223810fa123b179083a3aed53574706',
            'timestamp': 1466160960,
            'upload_date': '20160617',
            'uploader': 'B.C. & Lowy',
            'uploader_id': '232279340',
        },
    }, {
        'url': 'http://vlog.xuite.net/play/S1dDUjdyLTMyOTc3NjcuZmx2/%E5%AD%AB%E7%87%95%E5%A7%BF-%E7%9C%BC%E6%B7%9A%E6%88%90%E8%A9%A9',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        # /play/ URLs provide embedded video URL and more metadata
        url = url.replace('/embed/', '/play/')
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        error_msg = self._search_regex(
            r'<div id="error-message-content">([^<]+)',
            webpage, 'error message', default=None)
        if error_msg:
            raise ExtractorError(
                '%s returned error: %s' % (self.IE_NAME, error_msg),
                expected=True)

        media_info = self._parse_json(self._search_regex(
            r'var\s+mediaInfo\s*=\s*({.*});', webpage, 'media info'), video_id)

        video_id = media_info['MEDIA_ID']

        formats = []
        for key in ('html5Url', 'html5HQUrl'):
            video_url = media_info.get(key)
            if not video_url:
                continue
            format_id = self._search_regex(
                r'\bq=(.+?)\b', video_url, 'format id', default=None)
            formats.append({
                'url': video_url,
                'ext': 'mp4' if format_id.isnumeric() else format_id,
                'format_id': format_id,
                'height': int(format_id) if format_id.isnumeric() else None,
            })

        timestamp = media_info.get('PUBLISH_DATETIME')
        if timestamp:
            timestamp = parse_iso8601(timestamp + ' +0800', ' ')

        category = media_info.get('catName')
        categories = [category] if category else []

        uploader = media_info.get('NICKNAME')
        uploader_url = None

        author_div = get_element_by_attribute('itemprop', 'author', webpage)
        if author_div:
            uploader = uploader or self._html_search_meta('name', author_div)
            uploader_url = self._html_search_regex(
                r'<link[^>]+itemprop="url"[^>]+href="([^"]+)"', author_div,
                'uploader URL', fatal=False)

        return {
            'id': video_id,
            'title': media_info['TITLE'],
            'description': remove_end(media_info.get('metaDesc'), ' (Xuite 影音)'),
            'thumbnail': media_info.get('ogImageUrl'),
            'timestamp': timestamp,
            'uploader': uploader,
            'uploader_id': media_info.get('MEMBER_ID'),
            'uploader_url': uploader_url,
            'duration': float_or_none(media_info.get('MEDIA_DURATION'), 1000000),
            'categories': categories,
            'formats': formats,
        }
