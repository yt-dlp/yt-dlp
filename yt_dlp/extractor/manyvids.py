

from .common import InfoExtractor
from .. import traverse_obj
from ..utils import determine_ext, int_or_none, parse_count, parse_duration, parse_iso8601, url_or_none


class ManyVidsIE(InfoExtractor):
    _WORKING = True
    _VALID_URL = r'(?i)https?://(?:www\.)?manyvids\.com/video/(?P<id>\d+)'
    _TESTS = [
        {
            # Dead preview video
            'skip': True,
            'url': 'https://www.manyvids.com/Video/133957/everthing-about-me/',
            'md5': '03f11bb21c52dd12a05be21a5c7dcc97',
            'info_dict': {
                'id': '133957',
                'ext': 'mp4',
                'title': 'everthing about me (Preview)',
                'uploader': 'ellyxxix',
                'view_count': int,
                'like_count': int,
            },
        },
        {
            # preview video
            'url': 'https://www.manyvids.com/Video/530341/mv-tips-tricks',
            'md5': '738dc723f7735ee9602f7ea352a6d058',
            'info_dict': {
                'id': '530341',
                'ext': 'mp4',
                'title': 'MV Tips &amp; Tricks (Preview)',
                'description': 'md5:c3bae98c0f9453237c28b0f8795d9f83',
                'thumbnail': 'https://cdn5.manyvids.com/php_uploads/video_images/DestinyDiaz/thumbs/thumb_Hs26ATOO7fcZaI9sx3XT_screenshot_001.jpg',
                'uploader': 'DestinyDiaz',
                'view_count': int,
                'like_count': int,
                'release_timestamp': 1508419904,
                'tags': ['AdultSchool', 'BBW', 'SFW', 'TeacherFetish'],
                'release_date': '20171019',
                'duration': 3167.0,
            },
        },
        {
            # full video
            'url': 'https://www.manyvids.com/Video/935718/MY-FACE-REVEAL/',
            'md5': 'bb47bab0e0802c2a60c24ef079dfe60f',
            'info_dict': {
                'id': '935718',
                'ext': 'mp4',
                'title': 'MY FACE REVEAL',
                'description': 'md5:ec5901d41808b3746fed90face161612',
                'thumbnail': 'https://ods.manyvids.com/1001061960/3aa5397f2a723ec4597e344df66ab845/screenshots/thumbs/custom_1_180_5be09c1dcce03.jpg',
                'uploader': 'Sarah Calanthe',
                'view_count': int,
                'like_count': int,
                'release_date': '20181110',
                'tags': ['EyeContact', 'Interviews', 'MaskFetish', 'MouthFetish', 'Redhead'],
                'release_timestamp': 1541851200,
                'duration': 224.0,
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info = traverse_obj(
            self._download_json(f'https://www.manyvids.com/bff/store/video/{video_id}', video_id),
            ('data', {dict})) or {}

        video_urls = traverse_obj(
            self._download_json(f'https://www.manyvids.com/bff/store/video/{video_id}/private', video_id),
            ('data', {dict})) or {}

        video_urls_and_ids = (
            (traverse_obj(video_urls, ('teaser', 'filepath')), 'preview'),
            (video_urls.get('transcodedFilepath'), 'transcoded'),
            (video_urls.get('filepath'), 'filepath'),
        )

        title = info.get('title')
        uploader = traverse_obj(info, ('model', 'displayName'))
        description = info.get('description')
        likes = parse_count(info.get('likes'))
        views = parse_count(info.get('views'))
        thumbnail = url_or_none(info.get('screenshot')) or url_or_none(info.get('thumbnail'))
        release_timestamp = parse_iso8601(info.get('launchDate'))
        duration = parse_duration(info.get('videoDuration'))
        tags = [t.get('label') for t in info.get('tagList')]

        # If the video formats JSON only contains a teaser object, then it is a preview
        if video_urls.get('teaser') and not video_urls.get('filepath'):
            title += ' (Preview)'
            self.report_warning(
                f'Only extracting preview. Video may be paid or subscription only. {self._login_hint()}')

        formats = []
        for v_url, fmt in video_urls_and_ids:
            v_url = url_or_none(v_url)
            if not v_url:
                continue
            if determine_ext(v_url) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    v_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls'))
            else:
                formats.append({
                    'url': v_url,
                    'format_id': fmt,
                })

        self._remove_duplicate_formats(formats)

        for f in formats:
            if f.get('height') is None:
                f['height'] = int_or_none(
                    self._search_regex(r'_(\d{2,3}[02468])_', f['url'], 'video height', default=None))
            if 'preview' in f['format_id']:
                f['preference'] = -10
            if 'transcoded' in f['format_id']:
                f['preference'] = f.get('preference', -1) - 1

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': description,
            'uploader': uploader,
            'thumbnail': thumbnail,
            'view_count': views,
            'like_count': likes,
            'release_timestamp': release_timestamp,
            'duration': duration,
            'tags': tags,
        }
