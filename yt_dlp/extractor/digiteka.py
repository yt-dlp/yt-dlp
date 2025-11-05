from .common import InfoExtractor
from ..utils import determine_ext


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
        video_type = mobj.group('embed_type') or mobj.group('site_type')
        if video_type == 'music':
            video_type = 'musique'

        IFRAME_MD_ID = '01836272'   # Static ID for Ultimedia iframes
        iframe_json_ld_url = (
            f'https://www.ultimedia.com/deliver/generic/iframe/mdtk/{IFRAME_MD_ID}/zone/1/src/{video_id}'
        )

        iframe_webpage = self._download_webpage(
            iframe_json_ld_url, video_id, note='Downloading iframe JSON-LD', fatal=False)

        info = self._search_json_ld(iframe_webpage, video_id, 'VideoObject', fatal=False) or {}
        video_url = info.get('url')

        if not video_url:
            self.report_warning('JSON-LD "contentUrl" missing. Checking DtkPlayer JS for MP4 URL.')

            video_url = self._search_regex(
                r'"mp4_404"\s*:\s*"(https?:\\/\\/assets\.digiteka\.com\\/encoded\\/[^"]+\\/mp4\\/[^"]+_404\.mp4)"',
                iframe_webpage, 'MP4 404 URL', fatal=False)
            if video_url:
                video_url = video_url.replace('\\/', '/')

        if video_url:
            self.to_screen(f'{video_id}: SUCCESS: Using JSON-LD method.')

            title = info.get('title') or self._html_search_meta('title', iframe_webpage)
            formats = [{
                'url': video_url,
                'ext': determine_ext(video_url, 'mp4'),
                'format_id': 'hd',
            }]

            return {
                'id': video_id,
                'title': title,
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'timestamp': info.get('timestamp'),
                'formats': formats,
            }

        self.report_warning('JSON-LD extraction failed. Falling back to original API logic.')

        deliver_info = self._download_json(
            f'http://www.ultimedia.com/deliver/video?video={video_id}&topic={video_type}',
            video_id)

        yt_id = deliver_info.get('yt_id')
        if yt_id:
            return self.url_result(yt_id, 'Youtube')

        return {
            'formats': formats,
        }
