from .common import InfoExtractor
from ..utils import determine_ext


class AUltimediaVideoIE(InfoExtractor):
    _VALID_URL = r'''(?x)
    https?://(?:www\.)?(?:digiteka\.net|ultimedia\.com)/
    (?:
        # ... (patterns for 'deliver')
        |
        default/index/video
        (?P<site_type>
            generic|
            music
        )
        /id
    )/(?P<id>[\d+a-z]+)'''
    _TESTS = [{
        'url': 'https://www.ultimedia.com/default/index/videogeneric/id/3x5x55k',
        'info_dict': {
            'id': '3x5x55k',
            'ext': 'mp4',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        with open('webpage.txt', 'w', encoding='utf-8') as f:
            f.write(webpage)

        title = self._search_regex(
            r'<h1>\s*<div[^>]+id=["\']catArticle["\'][^>]*>[^<]+</div>\s*(.+?)\s*</h1>',
            webpage, 'title', fatal=True)

        description = self._html_search_regex(
            r'<div[^>]+class=["\']trunk6["\'][^>]*>(.+?)</div>',
            webpage, 'description', fatal=False)

        IFRAME_MD_ID = '01836272'           # Static ID for Ultimedia iframes
        iframe_json_ld_url = (
            f'https://www.ultimedia.com/deliver/generic/iframe/mdtk/{IFRAME_MD_ID}/zone/1/src/{video_id}'
        )

        self.to_screen(f'{video_id}: Downloading JSON-LD from direct iframe URL: {iframe_json_ld_url}')
        iframe_webpage = self._download_webpage(iframe_json_ld_url, video_id, note='Downloading iframe content')

        info = self._search_json_ld(iframe_webpage, video_id, 'VideoObject', fatal=True)
        video_url = info.get('url')

        formats = [{
            'url': video_url,
            'ext': determine_ext(video_url, 'mp4'),
        }]

        return {
            **info,
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
        }

    @staticmethod
    def ie_key():
        return 'AUltimeidaVideo'
