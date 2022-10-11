from .common import InfoExtractor
from .vimeo import VimeoIE


class AeonCoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?aeon\.co/videos/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://aeon.co/videos/raw-solar-storm-footage-is-the-punk-rock-antidote-to-sleek-james-webb-imagery',
        'md5': 'e5884d80552c9b6ea8d268a258753362',
        'info_dict': {
            'id': '1284717',
            'ext': 'mp4',
            'title': 'Brilliant Noise',
            'thumbnail': 'https://i.vimeocdn.com/video/21006315-1a1e49da8b07fd908384a982b4ba9ff0268c509a474576ebdf7b1392f4acae3b-d_960',
            'video_id': 'raw-solar-storm-footage-is-the-punk-rock-antidote-to-sleek-james-webb-imagery',
            'uploader': 'Semiconductor',
            'uploader_id': 'semiconductor',
            'uploader_url': 'https://vimeo.com/semiconductor',
            'duration': 348
        }
    }, {
        'url': 'https://aeon.co/videos/dazzling-timelapse-shows-how-microbes-spoil-our-food-and-sometimes-enrich-it',
        'md5': '4e5f3dad9dbda0dbfa2da41a851e631e',
        'info_dict': {
            'id': '728595228',
            'ext': 'mp4',
            'title': 'Wrought',
            'thumbnail': 'https://i.vimeocdn.com/video/1484618528-c91452611f9a4e4497735a533da60d45b2fe472deb0c880f0afaab0cd2efb22a-d_1280',
            'video_id': 'dazzling-timelapse-shows-how-microbes-spoil-our-food-and-sometimes-enrich-it',
            'uploader': 'Biofilm Productions',
            'uploader_id': 'user140352216',
            'uploader_url': 'https://vimeo.com/user140352216',
            'duration': 1344
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        vimeo_id = self._search_regex(r'hosterId\":\w*\"(?P<id>[0-9]+)', webpage, 'id')
        vimeo_url = f'https://player.vimeo.com/video/{vimeo_id}'
        referrer_url = VimeoIE._smuggle_referrer(vimeo_url, "https://aeon.co")

        return {
            'video_id': video_id,
            '_type': 'url_transparent',
            'url': referrer_url,
            'ie_key': 'Vimeo',
        }
