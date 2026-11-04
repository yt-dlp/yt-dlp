import base64

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import int_or_none, parse_duration, parse_iso8601, try_get


class TheGayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?thegay\.com/videos/(?P<id>[0-9]+)(/(?P<display_id>[^/]+))?'
    _TESTS = [{
        'url': 'https://thegay.com/videos/1034577/japanese-glossmen-muscle-hunk/',
        'md5': '007e8f44b7084c6acfb879580d73e891',
        'info_dict': {
            'age_limit': 18,
            'categories': ['Asian', 'Brunette', 'Japanese'],
            'comment_count': int,
            'description': '',
            'dislike_count': int,
            'display_id': 'japanese-glossmen-muscle-hunk',
            'duration': 479,
            'ext': 'mp4',
            'id': '1034577',
            'like_count': int,
            'thumbnail': 'https://tn.thegay.com/contents/videos_screenshots/1000000/1034577/preview.jpg',
            'timestamp': 1632013321,
            'title': 'Japanese Glossmen Muscle Hunk',
            'upload_date': '20210919',
            'uploader': 'Waylon Santoro',
            'uploader_id': 179643,
            'uploader_url': 'https://thegay.com/members/179643/',
            'view_count': int,
        },
    }]

    _homoglyph_mapping = {
        0x2c: '/',
        0x7e: '=',
        # ASCII characters are obfuscated by replacing them with similar-looking Cyrillic glyphs
        0x0410: 'A',
        0x0412: 'B',
        0x0415: 'E',
        0x041c: 'M',
        0x0421: 'C',
    }

    def _real_extract(self, url):
        match = self._match_valid_url(url)
        video_id = int_or_none(match.group('id'))
        display_id = match.group('display_id')

        api_json_url = 'https://thegay.com/api/json/video/86400/%d/%d/%d.json' % (1000000 * (video_id // 1000000), 1000 * (video_id // 1000), video_id)
        videofile_json_url = 'https://thegay.com/api/videofile.php?video_id=%d&lifetime=8640000' % (video_id)
        thumbnail_url = 'https://tn.thegay.com/contents/videos_screenshots/%d/%d/preview.jpg' % (1000000 * (video_id // 1000000), video_id)

        info_json = self._download_webpage(api_json_url, video_id)
        info = self._parse_json(info_json, video_id)
        video = info['video']

        uploader = try_get(video, lambda x: x['user']['username'], str)
        uploader_id = int_or_none(try_get(video, lambda x: x['user']['id']))
        uploader_url = 'https://thegay.com/members/%d/' % (uploader_id) if uploader_id else None

        # https://thegay.com/api/videofile.php?video_id=369099&lifetime=8640000
        videofile_json = self._download_webpage(videofile_json_url, video_id)
        videofile = self._parse_json(videofile_json, video_id)
        video_url_b64 = videofile[0]['video_url']
        video_url_b64 = video_url_b64.translate(self._homoglyph_mapping)
        video_path = base64.b64decode(video_url_b64).decode('utf8')
        video_url = 'https://thegay.com' + video_path

        video = info['video']

        categories = [value.get('title') for key, value in video.get('categories', {}).items()]

        return {
            'id': str(video_id),
            'display_id': display_id,
            'title': video.get('title'),
            'description': video.get('description'),
            'timestamp': parse_iso8601(video.get('post_date'), delimiter=' '),  # is a str "2022-09-19 01:02:03" in the JSON
            'uploader': uploader,
            'uploader_url': uploader_url,
            'uploader_id': uploader_id,
            'thumbnail': thumbnail_url,
            'duration': parse_duration(video.get('duration')),  # is a str "12:34" in the JSON
            'view_count': int_or_none(try_get(
                video, lambda x: x['statistics']['viewed'])),  # is a str in the JSON
            'like_count': int_or_none(try_get(
                video, lambda x: x['statistics']['likes'], int)),  # is an int in the JSON
            'dislike_count': int_or_none(try_get(
                video, lambda x: x['statistics']['dislikes'], int)),  # is an int in the JSON
            'comment_count': int_or_none(try_get(
                video, lambda x: x['statistics']['comments'])),  # is a str in the JSON
            'age_limit': 18,
            'categories': categories,

            'url': video_url,
        }
