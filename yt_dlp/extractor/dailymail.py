from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    determine_protocol,
    try_get,
    unescapeHTML,
)


class DailyMailIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dailymail\.co\.uk/(?:video/[^/]+/video-|embed/video/)(?P<id>[0-9]+)'
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=["\'](?P<url>(?:https?:)?//(?:www\.)?dailymail\.co\.uk/embed/video/\d+\.html)']
    _TESTS = [{
        'url': 'http://www.dailymail.co.uk/video/tvshowbiz/video-1295863/The-Mountain-appears-sparkling-water-ad-Heavy-Bubbles.html',
        'md5': 'f6129624562251f628296c3a9ffde124',
        'info_dict': {
            'id': '1295863',
            'ext': 'mp4',
            'title': 'The Mountain appears in sparkling water ad for \'Heavy Bubbles\'',
            'description': 'md5:a93d74b6da172dd5dc4d973e0b766a84',
        }
    }, {
        'url': 'http://www.dailymail.co.uk/embed/video/1295863.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_data = self._parse_json(self._search_regex(
            r"data-opts='({.+?})'", webpage, 'video data'), video_id)
        title = unescapeHTML(video_data['title'])

        sources_url = (try_get(
            video_data,
            (lambda x: x['plugins']['sources']['url'],
             lambda x: x['sources']['url']), compat_str)
            or 'http://www.dailymail.co.uk/api/player/%s/video-sources.json' % video_id)

        video_sources = self._download_json(sources_url, video_id)
        body = video_sources.get('body')
        if body:
            video_sources = body

        formats = []
        for rendition in video_sources['renditions']:
            rendition_url = rendition.get('url')
            if not rendition_url:
                continue
            tbr = int_or_none(rendition.get('encodingRate'), 1000)
            container = rendition.get('videoContainer')
            is_hls = container == 'M2TS'
            protocol = 'm3u8_native' if is_hls else determine_protocol({'url': rendition_url})
            formats.append({
                'format_id': ('hls' if is_hls else protocol) + ('-%d' % tbr if tbr else ''),
                'url': rendition_url,
                'width': int_or_none(rendition.get('frameWidth')),
                'height': int_or_none(rendition.get('frameHeight')),
                'tbr': tbr,
                'vcodec': rendition.get('videoCodec'),
                'container': container,
                'protocol': protocol,
                'ext': 'mp4' if is_hls else None,
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': unescapeHTML(video_data.get('descr')),
            'thumbnail': video_data.get('poster') or video_data.get('thumbnail'),
            'formats': formats,
        }
