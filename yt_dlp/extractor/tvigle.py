# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    parse_age_limit,
    try_get,
    url_or_none,
)


class TvigleIE(InfoExtractor):
    IE_NAME = 'tvigle'
    IE_DESC = 'Интернет-телевидение Tvigle.ru'
    _VALID_URL = r'https?://(?:www\.)?(?:tvigle\.ru/(?:[^/]+/)+(?P<display_id>[^/]+)/$|cloud\.tvigle\.ru/video/(?P<id>\d+))'

    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['RU']

    _TESTS = [
        {
            'url': 'http://www.tvigle.ru/video/sokrat/',
            'info_dict': {
                'id': '1848932',
                'display_id': 'sokrat',
                'ext': 'mp4',
                'title': 'Сократ',
                'description': 'md5:d6b92ffb7217b4b8ebad2e7665253c17',
                'duration': 6586,
                'age_limit': 12,
            },
            'skip': 'georestricted',
        },
        {
            'url': 'http://www.tvigle.ru/video/vladimir-vysotskii/vedushchii-teleprogrammy-60-minut-ssha-o-vladimire-vysotskom/',
            'info_dict': {
                'id': '5142516',
                'ext': 'flv',
                'title': 'Ведущий телепрограммы «60 минут» (США) о Владимире Высоцком',
                'description': 'md5:027f7dc872948f14c96d19b4178428a4',
                'duration': 186.080,
                'age_limit': 0,
            },
            'skip': 'georestricted',
        }, {
            'url': 'https://cloud.tvigle.ru/video/5267604/',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        if not video_id:
            webpage = self._download_webpage(url, display_id)
            video_id = self._html_search_regex(
                (r'<div[^>]+class=["\']player["\'][^>]+id=["\'](\d+)',
                 r'cloudId\s*=\s*["\'](\d+)',
                 r'class="video-preview current_playing" id="(\d+)"'),
                webpage, 'video id')

        video_data = self._download_json(
            'http://cloud.tvigle.ru/api/play/video/%s/' % video_id, display_id)

        item = video_data['playlist']['items'][0]

        videos = item.get('videos')

        error_message = item.get('errorMessage')
        if not videos and error_message:
            if item.get('isGeoBlocked') is True:
                self.raise_geo_restricted(
                    msg=error_message, countries=self._GEO_COUNTRIES)
            else:
                raise ExtractorError(
                    '%s returned error: %s' % (self.IE_NAME, error_message),
                    expected=True)

        title = item['title']
        description = item.get('description')
        thumbnail = item.get('thumbnail')
        duration = float_or_none(item.get('durationMilliseconds'), 1000)
        age_limit = parse_age_limit(item.get('ageRestrictions'))

        formats = []
        for vcodec, url_or_fmts in item['videos'].items():
            if vcodec == 'hls':
                m3u8_url = url_or_none(url_or_fmts)
                if not m3u8_url:
                    continue
                formats.extend(self._extract_m3u8_formats(
                    m3u8_url, video_id, ext='mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            elif vcodec == 'dash':
                mpd_url = url_or_none(url_or_fmts)
                if not mpd_url:
                    continue
                formats.extend(self._extract_mpd_formats(
                    mpd_url, video_id, mpd_id='dash', fatal=False))
            else:
                if not isinstance(url_or_fmts, dict):
                    continue
                for format_id, video_url in url_or_fmts.items():
                    if format_id == 'm3u8':
                        continue
                    video_url = url_or_none(video_url)
                    if not video_url:
                        continue
                    height = self._search_regex(
                        r'^(\d+)[pP]$', format_id, 'height', default=None)
                    filesize = int_or_none(try_get(
                        item, lambda x: x['video_files_size'][vcodec][format_id]))
                    formats.append({
                        'url': video_url,
                        'format_id': '%s-%s' % (vcodec, format_id),
                        'vcodec': vcodec,
                        'height': int_or_none(height),
                        'filesize': filesize,
                    })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': age_limit,
            'formats': formats,
        }
