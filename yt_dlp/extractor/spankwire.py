import re

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    merge_dicts,
    str_or_none,
    str_to_int,
    url_or_none,
)


class SpankwireIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?spankwire\.com/
                        (?:
                            [^/]+/video|
                            EmbedPlayer\.aspx/?\?.*?\bArticleId=
                        )
                        (?P<id>\d+)
                    '''
    _EMBED_REGEX = [r'<iframe[^>]+\bsrc=["\'](?P<url>(?:https?:)?//(?:www\.)?spankwire\.com/EmbedPlayer\.aspx/?\?.*?\bArticleId=\d+)']
    _TESTS = [{
        # download URL pattern: */<height>P_<tbr>K_<video_id>.mp4
        'url': 'http://www.spankwire.com/Buckcherry-s-X-Rated-Music-Video-Crazy-Bitch/video103545/',
        'md5': '5aa0e4feef20aad82cbcae3aed7ab7cd',
        'info_dict': {
            'id': '103545',
            'ext': 'mp4',
            'title': 'Buckcherry`s X Rated Music Video Crazy Bitch',
            'description': 'Crazy Bitch X rated music video.',
            'duration': 222,
            'uploader': 'oreusz',
            'uploader_id': '124697',
            'timestamp': 1178587885,
            'upload_date': '20070508',
            'average_rating': float,
            'view_count': int,
            'comment_count': int,
            'age_limit': 18,
            'categories': list,
            'tags': list,
        },
    }, {
        # download URL pattern: */mp4_<format_id>_<video_id>.mp4
        'url': 'http://www.spankwire.com/Titcums-Compiloation-I/video1921551/',
        'md5': '09b3c20833308b736ae8902db2f8d7e6',
        'info_dict': {
            'id': '1921551',
            'ext': 'mp4',
            'title': 'Titcums Compiloation I',
            'description': 'cum on tits',
            'uploader': 'dannyh78999',
            'uploader_id': '3056053',
            'upload_date': '20150822',
            'age_limit': 18,
        },
        'params': {
            'proxy': '127.0.0.1:8118'
        },
        'skip': 'removed',
    }, {
        'url': 'https://www.spankwire.com/EmbedPlayer.aspx/?ArticleId=156156&autostart=true',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'https://www.spankwire.com/api/video/%s.json' % video_id, video_id)

        title = video['title']

        formats = []
        videos = video.get('videos')
        if isinstance(videos, dict):
            for format_id, format_url in videos.items():
                video_url = url_or_none(format_url)
                if not format_url:
                    continue
                height = int_or_none(self._search_regex(
                    r'(\d+)[pP]', format_id, 'height', default=None))
                m = re.search(
                    r'/(?P<height>\d+)[pP]_(?P<tbr>\d+)[kK]', video_url)
                if m:
                    tbr = int(m.group('tbr'))
                    height = height or int(m.group('height'))
                else:
                    tbr = None
                formats.append({
                    'url': video_url,
                    'format_id': '%dp' % height if height else format_id,
                    'height': height,
                    'tbr': tbr,
                })
        m3u8_url = url_or_none(video.get('HLS'))
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=False))
        self._sort_formats(formats)

        view_count = str_to_int(video.get('viewed'))

        thumbnails = []
        for preference, t in enumerate(('', '2x'), start=0):
            thumbnail_url = url_or_none(video.get('poster%s' % t))
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'preference': preference,
            })

        def extract_names(key):
            entries_list = video.get(key)
            if not isinstance(entries_list, list):
                return
            entries = []
            for entry in entries_list:
                name = str_or_none(entry.get('name'))
                if name:
                    entries.append(name)
            return entries

        categories = extract_names('categories')
        tags = extract_names('tags')

        uploader = None
        info = {}

        webpage = self._download_webpage(
            'https://www.spankwire.com/_/video%s/' % video_id, video_id,
            fatal=False)
        if webpage:
            info = self._search_json_ld(webpage, video_id, default={})
            thumbnail_url = None
            if 'thumbnail' in info:
                thumbnail_url = url_or_none(info['thumbnail'])
                del info['thumbnail']
            if not thumbnail_url:
                thumbnail_url = self._og_search_thumbnail(webpage)
            if thumbnail_url:
                thumbnails.append({
                    'url': thumbnail_url,
                    'preference': 10,
                })
            uploader = self._html_search_regex(
                r'(?s)by\s*<a[^>]+\bclass=["\']uploaded__by[^>]*>(.+?)</a>',
                webpage, 'uploader', fatal=False)
            if not view_count:
                view_count = str_to_int(self._search_regex(
                    r'data-views=["\']([\d,.]+)', webpage, 'view count',
                    fatal=False))

        return merge_dicts({
            'id': video_id,
            'title': title,
            'description': video.get('description'),
            'duration': int_or_none(video.get('duration')),
            'thumbnails': thumbnails,
            'uploader': uploader,
            'uploader_id': str_or_none(video.get('userId')),
            'timestamp': int_or_none(video.get('time_approved_on')),
            'average_rating': float_or_none(video.get('rating')),
            'view_count': view_count,
            'comment_count': int_or_none(video.get('comments')),
            'age_limit': 18,
            'categories': categories,
            'tags': tags,
            'formats': formats,
        }, info)
