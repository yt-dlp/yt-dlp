import re

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    get_element_by_class,
    get_element_by_id,
    unified_strdate,
)


class FreesoundIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?freesound\.org/people/[^/]+/sounds/(?P<id>[^/]+)'
    _TEST = {
        'url': 'http://www.freesound.org/people/miklovan/sounds/194503/',
        'md5': '12280ceb42c81f19a515c745eae07650',
        'info_dict': {
            'id': '194503',
            'ext': 'mp3',
            'title': 'gulls in the city.wav',
            'description': 'the sounds of seagulls in the city',
            'duration': 130.233,
            'uploader': 'miklovan',
            'upload_date': '20130715',
            'tags': list,
        }
    }

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        webpage = self._download_webpage(url, audio_id)

        audio_url = self._og_search_property('audio', webpage, 'song url')
        title = self._og_search_property('audio:title', webpage, 'song title')

        description = self._html_search_regex(
            r'(?s)id=["\']sound_description["\'][^>]*>(.+?)</div>',
            webpage, 'description', fatal=False)

        duration = float_or_none(
            get_element_by_class('duration', webpage), scale=1000)

        upload_date = unified_strdate(get_element_by_id('sound_date', webpage))
        uploader = self._og_search_property(
            'audio:artist', webpage, 'uploader', fatal=False)

        channels = self._html_search_regex(
            r'Channels</dt><dd>(.+?)</dd>', webpage,
            'channels info', fatal=False)

        tags_str = get_element_by_class('tags', webpage)
        tags = re.findall(r'<a[^>]+>([^<]+)', tags_str) if tags_str else None

        audio_url = re.sub(r'^https?://freesound\.org(https?://)', r'\1', audio_url)
        audio_urls = [audio_url]

        LQ_FORMAT = '-lq.mp3'
        if LQ_FORMAT in audio_url:
            audio_urls.append(audio_url.replace(LQ_FORMAT, '-hq.mp3'))

        formats = [{
            'url': format_url,
            'format_note': channels,
            'quality': quality,
        } for quality, format_url in enumerate(audio_urls)]

        return {
            'id': audio_id,
            'title': title,
            'description': description,
            'duration': duration,
            'uploader': uploader,
            'upload_date': upload_date,
            'tags': tags,
            'formats': formats,
        }
