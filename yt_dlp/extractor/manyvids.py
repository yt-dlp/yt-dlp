from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    join_nonempty,
    parse_count,
    parse_duration,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class ManyVidsIE(InfoExtractor):
    _VALID_URL = r'(?i)https?://(?:www\.)?manyvids\.com/video/(?P<id>\d+)'
    _TESTS = [{
        # preview video
        'url': 'https://www.manyvids.com/Video/530341/mv-tips-tricks',
        'md5': '738dc723f7735ee9602f7ea352a6d058',
        'info_dict': {
            'id': '530341-preview',
            'ext': 'mp4',
            'title': 'MV Tips & Tricks (Preview)',
            'description': r're:I will take you on a tour around .{1313}$',
            'thumbnail': r're:https://cdn5\.manyvids\.com/php_uploads/video_images/DestinyDiaz/.+\.jpg',
            'uploader': 'DestinyDiaz',
            'view_count': int,
            'like_count': int,
            'release_timestamp': 1508419904,
            'tags': ['AdultSchool', 'BBW', 'SFW', 'TeacherFetish'],
            'release_date': '20171019',
            'duration': 3167.0,
        },
        'expected_warnings': ['Only extracting preview'],
    }, {
        # full video
        'url': 'https://www.manyvids.com/Video/935718/MY-FACE-REVEAL/',
        'md5': 'bb47bab0e0802c2a60c24ef079dfe60f',
        'info_dict': {
            'id': '935718',
            'ext': 'mp4',
            'title': 'MY FACE REVEAL',
            'description': r're:Today is the day!! I am finally taking off my mask .{445}$',
            'thumbnail': r're:https://ods\.manyvids\.com/1001061960/3aa5397f2a723ec4597e344df66ab845/screenshots/.+\.jpg',
            'uploader': 'Sarah Calanthe',
            'view_count': int,
            'like_count': int,
            'release_date': '20181110',
            'tags': ['EyeContact', 'Interviews', 'MaskFetish', 'MouthFetish', 'Redhead'],
            'release_timestamp': 1541851200,
            'duration': 224.0,
        },
    }]
    _API_BASE = 'https://www.manyvids.com/bff/store/video'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(f'{self._API_BASE}/{video_id}/private', video_id)['data']
        formats, preview_only = [], True

        for format_id, path in [
            ('preview', ['teaser', 'filepath']),
            ('transcoded', ['transcodedFilepath']),
            ('filepath', ['filepath']),
        ]:
            format_url = traverse_obj(video_data, (*path, {url_or_none}))
            if not format_url:
                continue
            if determine_ext(format_url) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(format_url, video_id, 'mp4', m3u8_id=format_id))
            else:
                formats.append({
                    'url': format_url,
                    'format_id': format_id,
                    'preference': -10 if format_id == 'preview' else None,
                    'quality': 10 if format_id == 'filepath' else None,
                    'height': int_or_none(
                        self._search_regex(r'_(\d{2,3}[02468])_', format_url, 'height', default=None)),
                })
            if format_id != 'preview':
                preview_only = False

        metadata = traverse_obj(
            self._download_json(f'{self._API_BASE}/{video_id}', video_id, fatal=False), 'data')
        title = traverse_obj(metadata, ('title', {clean_html}))

        if preview_only:
            title = join_nonempty(title, '(Preview)', delim=' ')
            video_id += '-preview'
            self.report_warning(
                f'Only extracting preview. Video may be paid or subscription only. {self._login_hint()}')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            **traverse_obj(metadata, {
                'description': ('description', {clean_html}),
                'uploader': ('model', 'displayName', {clean_html}),
                'thumbnail': (('screenshot', 'thumbnail'), {url_or_none}, any),
                'view_count': ('views', {parse_count}),
                'like_count': ('likes', {parse_count}),
                'release_timestamp': ('launchDate', {parse_iso8601}),
                'duration': ('videoDuration', {parse_duration}),
                'tags': ('tagList', ..., 'label', {str}, filter, all, filter),
            }),
        }
