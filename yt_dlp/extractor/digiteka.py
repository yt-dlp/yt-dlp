from .common import InfoExtractor
from ..utils import int_or_none, url_or_none
from ..utils.traversal import traverse_obj


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
    _IFRAME_MD_ID = '01836272'   # One static ID working for Ultimedia iframes

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_info = self._download_json(
            f'https://www.ultimedia.com/player/getConf/{self._IFRAME_MD_ID}/1/{video_id}', video_id,
            note='Downloading player configuration')['video']

        formats = []
        subtitles = {}

        if hls_url := traverse_obj(video_info, ('media_sources', 'hls', 'hls_auto', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                hls_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        for format_id, mp4_url in traverse_obj(video_info, ('media_sources', 'mp4', {dict.items}, ...)):
            if not mp4_url:
                continue
            formats.append({
                'url': mp4_url,
                'format_id': format_id,
                'height': int_or_none(format_id.partition('_')[2]),
                'ext': 'mp4',
            })

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_info, {
                'title': ('title', {str}),
                'thumbnail': ('image', {url_or_none}),
                'duration': ('duration', {int_or_none}),
                'timestamp': ('creationDate', {int_or_none}),
                'uploader_id': ('ownerId', {str}),
            }),
        }
