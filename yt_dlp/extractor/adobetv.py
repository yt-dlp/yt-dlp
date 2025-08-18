from .common import InfoExtractor
from ..utils import (
    ISO639Utils,
    clean_html,
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class AdobeTVVideoIE(InfoExtractor):
    IE_NAME = 'adobetv'
    _VALID_URL = r'https?://video\.tv\.adobe\.com/v/(?P<id>\d+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=["\'](?P<url>(?:https?:)?//video\.tv\.adobe\.com/v/\d+)']
    _TESTS = [{
        'url': 'https://video.tv.adobe.com/v/2456',
        'md5': '43662b577c018ad707a63766462b1e87',
        'info_dict': {
            'id': '2456',
            'ext': 'mp4',
            'title': 'New experience with Acrobat DC',
            'description': 'New experience with Acrobat DC',
            'duration': 248.522,
            'thumbnail': r're:https?://images-tv\.adobe\.com/.+\.jpg',
        },
    }, {
        'url': 'https://video.tv.adobe.com/v/3463980/adobe-acrobat',
        'info_dict': {
            'id': '3463980',
            'ext': 'mp4',
            'title': 'Adobe Acrobat: How to Customize the Toolbar for Faster PDF Editing',
            'description': 'md5:94368ab95ae24f9c1bee0cb346e03dc3',
            'duration': 97.514,
            'thumbnail': r're:https?://images-tv\.adobe\.com/.+\.jpg',
        },
    }]
    _WEBPAGE_TESTS = [{
        # https://video.tv.adobe.com/v/3442499
        'url': 'https://business.adobe.com/dx-fragments/summit/2025/marquees/S335/ondemand.live.html',
        'info_dict': {
            'id': '3442499',
            'ext': 'mp4',
            'title': 'S335 - Beyond Personalization: Creating Intent-Based Experiences at Scale',
            'description': 'Beyond Personalization: Creating Intent-Based Experiences at Scale',
            'duration': 2906.8,
            'thumbnail': r're:https?://images-tv\.adobe\.com/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_data = self._search_json(
            r'var\s+bridge\s*=', webpage, 'bridged data', video_id)

        formats = []
        for source in traverse_obj(video_data, (
            'sources', lambda _, v: v['format'] != 'playlist' and url_or_none(v['src']),
        )):
            source_url = self._proto_relative_url(source['src'])
            if determine_ext(source_url) == 'm3u8':
                fmts = self._extract_m3u8_formats(
                    source_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            else:
                fmts = [{'url': source_url}]

            for fmt in fmts:
                fmt.update(traverse_obj(source, {
                    'duration': ('duration', {float_or_none(scale=1000)}),
                    'filesize': ('kilobytes', {float_or_none(invscale=1000)}),
                    'format_id': (('format', 'label'), {str}, all, {lambda x: join_nonempty(*x)}),
                    'height': ('height', {int_or_none}),
                    'tbr': ('bitrate', {int_or_none}),
                    'width': ('width', {int_or_none}),
                }))
            formats.extend(fmts)

        subtitles = {}
        for translation in traverse_obj(video_data, (
            'translations', lambda _, v: url_or_none(v['vttPath']),
        )):
            lang = translation.get('language_w3c') or ISO639Utils.long2short(translation.get('language_medium')) or 'und'
            subtitles.setdefault(lang, []).append({
                'ext': 'vtt',
                'url': self._proto_relative_url(translation['vttPath']),
            })

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_data, {
                'title': ('title', {clean_html}),
                'description': ('description', {clean_html}, filter),
                'thumbnail': ('video', 'poster', {self._proto_relative_url}, {url_or_none}),
            }),
        }
