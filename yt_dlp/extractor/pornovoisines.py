from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    unified_strdate,
)


class PornoVoisinesIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?pornovoisines\.com/videos/show/(?P<id>\d+)/(?P<display_id>[^/.]+)'

    _TEST = {
        'url': 'http://www.pornovoisines.com/videos/show/919/recherche-appartement.html',
        'md5': '6f8aca6a058592ab49fe701c8ba8317b',
        'info_dict': {
            'id': '919',
            'display_id': 'recherche-appartement',
            'ext': 'mp4',
            'title': 'Recherche appartement',
            'description': 'md5:fe10cb92ae2dd3ed94bb4080d11ff493',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20140925',
            'duration': 120,
            'view_count': int,
            'average_rating': float,
            'categories': ['Débutante', 'Débutantes', 'Scénario', 'Sodomie'],
            'age_limit': 18,
            'subtitles': {
                'fr': [{
                    'ext': 'vtt',
                }],
            },
        },
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        settings_url = self._download_json(
            f'http://www.pornovoisines.com/api/video/{video_id}/getsettingsurl/',
            video_id, note='Getting settings URL')['video_settings_url']
        settings = self._download_json(settings_url, video_id)['data']

        formats = []
        for kind, data in settings['variants'].items():
            if kind == 'HLS':
                formats.extend(self._extract_m3u8_formats(
                    data, video_id, ext='mp4', entry_protocol='m3u8_native', m3u8_id='hls'))
            elif kind == 'MP4':
                for item in data:
                    formats.append({
                        'url': item['url'],
                        'height': item.get('height'),
                        'bitrate': item.get('bitrate'),
                    })

        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(webpage)
        description = self._og_search_description(webpage)

        # The webpage has a bug - there's no space between "thumb" and src=
        thumbnail = self._html_search_regex(
            r'<img[^>]+class=([\'"])thumb\1[^>]*src=([\'"])(?P<url>[^"]+)\2',
            webpage, 'thumbnail', fatal=False, group='url')

        upload_date = unified_strdate(self._search_regex(
            r'Le\s*<b>([\d/]+)', webpage, 'upload date', fatal=False))
        duration = settings.get('main', {}).get('duration')
        view_count = int_or_none(self._search_regex(
            r'(\d+) vues', webpage, 'view count', fatal=False))
        average_rating = self._search_regex(
            r'Note\s*:\s*(\d+(?:,\d+)?)', webpage, 'average rating', fatal=False)
        if average_rating:
            average_rating = float_or_none(average_rating.replace(',', '.'))

        categories = self._html_search_regex(
            r'(?s)Catégories\s*:\s*<b>(.+?)</b>', webpage, 'categories', fatal=False)
        if categories:
            categories = [category.strip() for category in categories.split(',')]

        subtitles = {'fr': [{
            'url': subtitle,
        } for subtitle in settings.get('main', {}).get('vtt_tracks', {}).values()]}

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'average_rating': average_rating,
            'categories': categories,
            'age_limit': 18,
            'subtitles': subtitles,
        }
