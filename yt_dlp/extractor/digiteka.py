from .common import InfoExtractor
from ..utils import ExtractorError


class DigitekaIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?(?:digiteka\.net|ultimedia\.com)/
        (?:
            deliver/
            (?P<embed_type>
                generic|
                musique
            )
            (?:/[^/]+)*/
            (?:
                src|
                article
            )|
            default/index/video
            (?P<site_type>
                generic|
                music
            )
            /id
        )/(?P<id>[\d+a-z]+)'''
    _EMBED_REGEX = [r'<(?:iframe|script)[^>]+src=["\'](?P<url>(?:https?:)?//(?:www\.)?ultimedia\.com/deliver/(?:generic|musique)(?:/[^/]+)*/(?:src|article)/[\d+a-z]+)']
    _TESTS = [{
        'url': 'https://www.ultimedia.com/default/index/videogeneric/id/3x5x55k',
        'info_dict': {
            'id': '3x5x55k',
            'ext': 'mp4',
            'title': 'Il est passionné de DS',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 89,
            'upload_date': '20251012',
            'timestamp': 1760285363,
            'uploader_id': '3pz33',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        IFRAME_MD_ID = '01836272'   # One static ID working for Ultimedia iframes

        api_url = f'https://www.ultimedia.com/player/getConf/{IFRAME_MD_ID}/1/{video_id}'

        conf_data = self._download_json(
            api_url, video_id, note='Downloading player configuration')

        video_info = conf_data.get('video')
        if not video_info:
            raise ExtractorError('Failed to retrieve video information from API.', expected=True)

        title = video_info['title']
        formats = []
        media_sources = video_info.get('media_sources', {})

        hls_sources = media_sources.get('hls', {})
        for format_id, hls_url in hls_sources.items():
            if not hls_url:
                continue

            height_str = format_id.split('_')[-1]
            height = int(height_str) if height_str.isdigit() else None

            formats.append({
                'url': hls_url,
                'format_id': f'hls-{height_str}',
                'height': height,
                'protocol': 'm3u8_native',
                'ext': 'mp4',
            })

        mp4_sources = media_sources.get('mp4', {})
        for format_id, mp4_url in mp4_sources.items():
            if not mp4_url:
                continue

            height_str = format_id.split('_')[-1]
            height = int(height_str) if height_str.isdigit() else None

            formats.append({
                'url': mp4_url,
                'format_id': f'mp4-{height_str}',
                'height': height,
                'ext': 'mp4',
            })

        yt_id = video_info.get('yt_id')
        if yt_id:
            return self.url_result(yt_id, 'Youtube')

        if not formats:
            raise ExtractorError('No video formats found.', expected=True)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': video_info.get('image'),
            'duration': video_info.get('duration'),
            'timestamp': video_info.get('creationDate'),
            'uploader_id': video_info.get('ownerId'),
            'formats': formats,
        }
