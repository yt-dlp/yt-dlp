from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    parse_iso8601,
    parse_duration,
)


class SkyNewsArabiaBaseIE(InfoExtractor):
    _IMAGE_BASE_URL = 'http://www.skynewsarabia.com/web/images'

    def _call_api(self, path, value):
        return self._download_json('http://api.skynewsarabia.com/web/rest/v2/%s/%s.json' % (path, value), value)

    def _get_limelight_media_id(self, url):
        return self._search_regex(r'/media/[^/]+/([a-z0-9]{32})', url, 'limelight media id')

    def _get_image_url(self, image_path_template, width='1600', height='1200'):
        return self._IMAGE_BASE_URL + image_path_template.format(width=width, height=height)

    def _extract_video_info(self, video_data):
        video_id = compat_str(video_data['id'])
        topic = video_data.get('topicTitle')
        return {
            '_type': 'url_transparent',
            'url': 'limelight:media:%s' % self._get_limelight_media_id(video_data['videoUrl'][0]['url']),
            'id': video_id,
            'title': video_data['headline'],
            'description': video_data.get('summary'),
            'thumbnail': self._get_image_url(video_data['mediaAsset']['imageUrl']),
            'timestamp': parse_iso8601(video_data.get('date')),
            'duration': parse_duration(video_data.get('runTime')),
            'tags': video_data.get('tags', []),
            'categories': [topic] if topic else [],
            'webpage_url': 'http://www.skynewsarabia.com/web/video/%s' % video_id,
            'ie_key': 'LimelightMedia',
        }


class SkyNewsArabiaIE(SkyNewsArabiaBaseIE):
    IE_NAME = 'skynewsarabia:video'
    _VALID_URL = r'https?://(?:www\.)?skynewsarabia\.com/web/video/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://www.skynewsarabia.com/web/video/794902/%D9%86%D8%B5%D9%81-%D9%85%D9%84%D9%8A%D9%88%D9%86-%D9%85%D8%B5%D8%A8%D8%A7%D8%AD-%D8%B4%D8%AC%D8%B1%D8%A9-%D9%83%D8%B1%D9%8A%D8%B3%D9%85%D8%A7%D8%B3',
        'info_dict': {
            'id': '794902',
            'ext': 'flv',
            'title': 'نصف مليون مصباح على شجرة كريسماس',
            'description': 'md5:22f1b27f0850eeb10c7e59b1f16eb7c6',
            'upload_date': '20151128',
            'timestamp': 1448697198,
            'duration': 2119,
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._call_api('video', video_id)
        return self._extract_video_info(video_data)


class SkyNewsArabiaArticleIE(SkyNewsArabiaBaseIE):
    IE_NAME = 'skynewsarabia:article'
    _VALID_URL = r'https?://(?:www\.)?skynewsarabia\.com/web/article/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.skynewsarabia.com/web/article/794549/%D8%A7%D9%94%D8%AD%D8%AF%D8%A7%D8%AB-%D8%A7%D9%84%D8%B4%D8%B1%D9%82-%D8%A7%D9%84%D8%A7%D9%94%D9%88%D8%B3%D8%B7-%D8%AE%D8%B1%D9%8A%D8%B7%D8%A9-%D8%A7%D9%84%D8%A7%D9%94%D9%84%D8%B9%D8%A7%D8%A8-%D8%A7%D9%84%D8%B0%D9%83%D9%8A%D8%A9',
        'info_dict': {
            'id': '794549',
            'ext': 'flv',
            'title': 'بالفيديو.. ألعاب ذكية تحاكي واقع المنطقة',
            'description': 'md5:0c373d29919a851e080ee4edd0c5d97f',
            'upload_date': '20151126',
            'timestamp': 1448559336,
            'duration': 281.6,
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.skynewsarabia.com/web/article/794844/%D8%A7%D8%B3%D8%AA%D9%87%D8%AF%D8%A7%D9%81-%D9%82%D9%88%D8%A7%D8%B1%D8%A8-%D8%A7%D9%94%D8%B3%D9%84%D8%AD%D8%A9-%D9%84%D9%85%D9%8A%D9%84%D9%8A%D8%B4%D9%8A%D8%A7%D8%AA-%D8%A7%D9%84%D8%AD%D9%88%D8%AB%D9%8A-%D9%88%D8%B5%D8%A7%D9%84%D8%AD',
        'info_dict': {
            'id': '794844',
            'title': 'إحباط تهريب أسلحة لميليشيات الحوثي وصالح بجنوب اليمن',
            'description': 'md5:5c927b8b2e805796e7f693538d96fc7e',
        },
        'playlist_mincount': 2,
    }]

    def _real_extract(self, url):
        article_id = self._match_id(url)
        article_data = self._call_api('article', article_id)
        media_asset = article_data['mediaAsset']
        if media_asset['type'] == 'VIDEO':
            topic = article_data.get('topicTitle')
            return {
                '_type': 'url_transparent',
                'url': 'limelight:media:%s' % self._get_limelight_media_id(media_asset['videoUrl'][0]['url']),
                'id': article_id,
                'title': article_data['headline'],
                'description': article_data.get('summary'),
                'thumbnail': self._get_image_url(media_asset['imageUrl']),
                'timestamp': parse_iso8601(article_data.get('date')),
                'tags': article_data.get('tags', []),
                'categories': [topic] if topic else [],
                'webpage_url': url,
                'ie_key': 'LimelightMedia',
            }
        entries = [self._extract_video_info(item) for item in article_data.get('inlineItems', []) if item['type'] == 'VIDEO']
        return self.playlist_result(entries, article_id, article_data['headline'], article_data.get('summary'))
