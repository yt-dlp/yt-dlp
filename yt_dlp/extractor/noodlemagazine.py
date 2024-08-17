from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_count,
    parse_duration,
    unified_strdate,
    urljoin,
)
from ..utils.traversal import traverse_obj


class NoodleMagazineIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|adult\.)?noodlemagazine\.com/watch/(?P<id>[0-9-_]+)'
    _TEST = {
        'url': 'https://adult.noodlemagazine.com/watch/-67421364_456239604',
        'md5': '9e02aa763612929d0b4b850591a9248b',
        'info_dict': {
            'id': '-67421364_456239604',
            'title': 'Aria alexander manojob',
            'thumbnail': r're:^https://.*\.jpg',
            'ext': 'mp4',
            'duration': 903,
            'view_count': int,
            'like_count': int,
            'description': 'Aria alexander manojob',
            'tags': ['aria', 'alexander', 'manojob'],
            'upload_date': '20190218',
            'age_limit': 18,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage)
        duration = parse_duration(self._html_search_meta('video:duration', webpage, 'duration', default=None))
        description = self._og_search_property('description', webpage, default='').replace(' watch online hight quality video', '')
        tags = self._html_search_meta('video:tag', webpage, default='').split(', ')
        view_count = parse_count(self._html_search_meta('ya:ovs:views_total', webpage, default=None))
        like_count = parse_count(self._html_search_meta('ya:ovs:likes', webpage, default=None))
        upload_date = unified_strdate(self._html_search_meta('ya:ovs:upload_date', webpage, default=''))

        def build_url(url_or_path):
            return urljoin('https://adult.noodlemagazine.com', url_or_path)

        headers = {'Referer': url}
        player_path = self._html_search_regex(
            r'<iframe[^>]+\bid="iplayer"[^>]+\bsrc="([^"]+)"', webpage, 'player path')
        player_iframe = self._download_webpage(
            build_url(player_path), video_id, 'Downloading iframe page', headers=headers)
        playlist_url = self._search_regex(
            r'window\.playlistUrl\s*=\s*["\']([^"\']+)["\']', player_iframe, 'playlist url')
        playlist_info = self._download_json(build_url(playlist_url), video_id, headers=headers)

        formats = []
        for source in traverse_obj(playlist_info, ('sources', lambda _, v: v['file'])):
            if source.get('type') == 'hls':
                formats.extend(self._extract_m3u8_formats(
                    build_url(source['file']), video_id, 'mp4', fatal=False, m3u8_id='hls'))
            else:
                formats.append(traverse_obj(source, {
                    'url': ('file', {build_url}),
                    'format_id': 'label',
                    'height': ('label', {int_or_none}),
                    'ext': 'type',
                }))

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'thumbnail': self._og_search_property('image', webpage, default=None) or playlist_info.get('image'),
            'duration': duration,
            'description': description,
            'tags': tags,
            'view_count': view_count,
            'like_count': like_count,
            'upload_date': upload_date,
            'age_limit': 18,
        }
