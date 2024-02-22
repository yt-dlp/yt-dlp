from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    merge_dicts,
    str_to_int,
    unified_strdate,
    url_or_none,
    urljoin,
)


class RedTubeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:\w+\.)?redtube\.com(?:\.br)?/|embed\.redtube\.com/\?.*?\bid=)(?P<id>[0-9]+)'
    _EMBED_REGEX = [r'<iframe[^>]+?src=["\'](?P<url>(?:https?:)?//embed\.redtube\.com/\?.*?\bid=\d+)']
    _TESTS = [{
        'url': 'https://www.redtube.com/38864951',
        'md5': '4fba70cbca3aefd25767ab4b523c9878',
        'info_dict': {
            'id': '38864951',
            'ext': 'mp4',
            'title': 'Public Sex on the Balcony in Freezing Paris! Amateur Couple LeoLulu',
            'description': 'Watch video Public Sex on the Balcony in Freezing Paris! Amateur Couple LeoLulu on Redtube, home of free Blowjob porn videos and Blonde sex movies online. Video length: (10:46) - Uploaded by leolulu - Verified User - Starring Pornstar: Leolulu',
            'upload_date': '20210111',
            'timestamp': 1610343109,
            'duration': 646,
            'view_count': int,
            'age_limit': 18,
            'thumbnail': r're:https://\wi-ph\.rdtcdn\.com/videos/.+/.+\.jpg',
        },
    }, {
        'url': 'http://embed.redtube.com/?bgcolor=000000&id=1443286',
        'only_matching': True,
    }, {
        'url': 'http://it.redtube.com/66418',
        'only_matching': True,
    }, {
        'url': 'https://www.redtube.com.br/103224331',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            f'https://www.redtube.com/{video_id}', video_id)

        ERRORS = (
            (('video-deleted-info', '>This video has been removed'), 'has been removed'),
            (('private_video_text', '>This video is private', '>Send a friend request to its owner to be able to view it'), 'is private'),
        )

        for patterns, message in ERRORS:
            if any(p in webpage for p in patterns):
                raise ExtractorError(
                    'Video %s %s' % (video_id, message), expected=True)

        info = self._search_json_ld(webpage, video_id, default={})

        if not info.get('title'):
            info['title'] = self._html_search_regex(
                (r'<h(\d)[^>]+class="(?:video_title_text|videoTitle|video_title)[^"]*">(?P<title>(?:(?!\1).)+)</h\1>',
                 r'(?:videoTitle|title)\s*:\s*(["\'])(?P<title>(?:(?!\1).)+)\1',),
                webpage, 'title', group='title',
                default=None) or self._og_search_title(webpage)

        formats = []
        sources = self._parse_json(
            self._search_regex(
                r'sources\s*:\s*({.+?})', webpage, 'source', default='{}'),
            video_id, fatal=False)
        if sources and isinstance(sources, dict):
            for format_id, format_url in sources.items():
                if format_url:
                    formats.append({
                        'url': format_url,
                        'format_id': format_id,
                        'height': int_or_none(format_id),
                    })
        medias = self._parse_json(
            self._search_regex(
                r'mediaDefinition["\']?\s*:\s*(\[.+?}\s*\])', webpage,
                'media definitions', default='{}'),
            video_id, fatal=False)
        for media in medias if isinstance(medias, list) else []:
            format_url = urljoin('https://www.redtube.com', media.get('videoUrl'))
            if not format_url:
                continue
            format_id = media.get('format')
            quality = media.get('quality')
            if format_id == 'hls' or (format_id == 'mp4' and not quality):
                more_media = self._download_json(format_url, video_id, fatal=False)
            else:
                more_media = [media]
            for media in more_media if isinstance(more_media, list) else []:
                format_url = url_or_none(media.get('videoUrl'))
                if not format_url:
                    continue
                format_id = media.get('format')
                if format_id == 'hls' or determine_ext(format_url) == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        format_url, video_id, 'mp4',
                        entry_protocol='m3u8_native', m3u8_id=format_id or 'hls',
                        fatal=False))
                    continue
                format_id = media.get('quality')
                formats.append({
                    'url': format_url,
                    'ext': 'mp4',
                    'format_id': format_id,
                    'height': int_or_none(format_id),
                })
        if not formats:
            video_url = self._html_search_regex(
                r'<source src="(.+?)" type="video/mp4">', webpage, 'video URL')
            formats.append({'url': video_url, 'ext': 'mp4'})

        thumbnail = self._og_search_thumbnail(webpage)
        upload_date = unified_strdate(self._search_regex(
            r'<span[^>]+>(?:ADDED|Published on) ([^<]+)<',
            webpage, 'upload date', default=None))
        duration = int_or_none(self._og_search_property(
            'video:duration', webpage, default=None) or self._search_regex(
                r'videoDuration\s*:\s*(\d+)', webpage, 'duration', default=None))
        view_count = str_to_int(self._search_regex(
            (r'<div[^>]*>Views</div>\s*<div[^>]*>\s*([\d,.]+)',
             r'<span[^>]*>VIEWS</span>\s*</td>\s*<td>\s*([\d,.]+)',
             r'<span[^>]+\bclass=["\']video_view_count[^>]*>\s*([\d,.]+)'),
            webpage, 'view count', default=None))

        # No self-labeling, but they describe themselves as
        # "Home of Videos Porno"
        age_limit = 18

        return merge_dicts(info, {
            'id': video_id,
            'ext': 'mp4',
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'age_limit': age_limit,
            'formats': formats,
        })
