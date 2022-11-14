from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unified_strdate,
)


class ExpoTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?expotv\.com/videos/[^?#]*/(?P<id>[0-9]+)($|[?#])'
    _TEST = {
        'url': 'http://www.expotv.com/videos/reviews/3/40/NYX-Butter-lipstick/667916',
        'md5': 'fe1d728c3a813ff78f595bc8b7a707a8',
        'info_dict': {
            'id': '667916',
            'ext': 'mp4',
            'title': 'NYX Butter Lipstick Little Susie',
            'description': 'Goes on like butter, but looks better!',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Stephanie S.',
            'upload_date': '20150520',
            'view_count': int,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        player_key = self._search_regex(
            r'<param name="playerKey" value="([^"]+)"', webpage, 'player key')
        config = self._download_json(
            'http://client.expotv.com/video/config/%s/%s' % (video_id, player_key),
            video_id, 'Downloading video configuration')

        formats = []
        for fcfg in config['sources']:
            media_url = fcfg.get('file')
            if not media_url:
                continue
            if fcfg.get('type') == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    media_url, video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls'))
            else:
                formats.append({
                    'url': media_url,
                    'height': int_or_none(fcfg.get('height')),
                    'format_id': fcfg.get('label'),
                    'ext': self._search_regex(
                        r'filename=.*\.([a-z0-9_A-Z]+)&', media_url,
                        'file extension', default=None) or fcfg.get('type'),
                })
        self._sort_formats(formats)

        title = self._og_search_title(webpage)
        description = self._og_search_description(webpage)
        thumbnail = config.get('image')
        view_count = int_or_none(self._search_regex(
            r'<h5>Plays: ([0-9]+)</h5>', webpage, 'view counts'))
        uploader = self._search_regex(
            r'<div class="reviewer">\s*<img alt="([^"]+)"', webpage, 'uploader',
            fatal=False)
        upload_date = unified_strdate(self._search_regex(
            r'<h5>Reviewed on ([0-9/.]+)</h5>', webpage, 'upload date',
            fatal=False), day_first=False)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': description,
            'view_count': view_count,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'upload_date': upload_date,
        }
