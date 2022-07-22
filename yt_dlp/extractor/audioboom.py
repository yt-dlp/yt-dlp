from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
)


class AudioBoomIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?audioboom\.com/(?:boos|posts)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://audioboom.com/posts/7398103-asim-chaudhry',
        'md5': '7b00192e593ff227e6a315486979a42d',
        'info_dict': {
            'id': '7398103',
            'ext': 'mp3',
            'title': 'Asim Chaudhry',
            'description': 'md5:2f3fef17dacc2595b5362e1d7d3602fc',
            'duration': 4000.99,
            'uploader': 'Sue Perkins: An hour or so with...',
            'uploader_url': r're:https?://(?:www\.)?audioboom\.com/channel/perkins',
        }
    }, {
        'url': 'https://audioboom.com/posts/4279833-3-09-2016-czaban-hour-3?t=0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        clip = None

        clip_store = self._parse_json(
            self._html_search_regex(
                r'data-new-clip-store=(["\'])(?P<json>{.+?})\1',
                webpage, 'clip store', default='{}', group='json'),
            video_id, fatal=False)
        if clip_store:
            clips = clip_store.get('clips')
            if clips and isinstance(clips, list) and isinstance(clips[0], dict):
                clip = clips[0]

        def from_clip(field):
            if clip:
                return clip.get(field)

        audio_url = from_clip('clipURLPriorToLoading') or self._og_search_property(
            'audio', webpage, 'audio url')
        title = from_clip('title') or self._html_search_meta(
            ['og:title', 'og:audio:title', 'audio_title'], webpage)
        description = from_clip('description') or clean_html(from_clip('formattedDescription')) or self._og_search_description(webpage)

        duration = float_or_none(from_clip('duration') or self._html_search_meta(
            'weibo:audio:duration', webpage))

        uploader = from_clip('author') or self._html_search_meta(
            ['og:audio:artist', 'twitter:audio:artist_name', 'audio_artist'], webpage, 'uploader')
        uploader_url = from_clip('author_url') or self._html_search_meta(
            'audioboo:channel', webpage, 'uploader url')

        return {
            'id': video_id,
            'url': audio_url,
            'title': title,
            'description': description,
            'duration': duration,
            'uploader': uploader,
            'uploader_url': uploader_url,
        }
