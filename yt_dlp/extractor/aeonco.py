from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import ExtractorError, traverse_obj, url_or_none


class AeonCoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?aeon\.co/videos/(?P<id>[^/?]+)'
    _TESTS = [{
        'url': 'https://aeon.co/videos/raw-solar-storm-footage-is-the-punk-rock-antidote-to-sleek-james-webb-imagery',
        'md5': 'e5884d80552c9b6ea8d268a258753362',
        'info_dict': {
            'id': '1284717',
            'ext': 'mp4',
            'title': 'Brilliant Noise',
            'thumbnail': 'https://i.vimeocdn.com/video/21006315-1a1e49da8b07fd908384a982b4ba9ff0268c509a474576ebdf7b1392f4acae3b-d_960',
            'uploader': 'Semiconductor',
            'uploader_id': 'semiconductor',
            'uploader_url': 'https://vimeo.com/semiconductor',
            'duration': 348
        }
    }, {
        'url': 'https://aeon.co/videos/dazzling-timelapse-shows-how-microbes-spoil-our-food-and-sometimes-enrich-it',
        'md5': '03582d795382e49f2fd0b427b55de409',
        'info_dict': {
            'id': '759576926',
            'ext': 'mp4',
            'title': 'Wrought',
            'thumbnail': 'https://i.vimeocdn.com/video/1525599692-84614af88e446612f49ca966cf8f80eab2c73376bedd80555741c521c26f9a3e-d_1280',
            'uploader': 'Aeon Video',
            'uploader_id': 'aeonvideo',
            'uploader_url': 'https://vimeo.com/aeonvideo',
            'duration': 1344
        }
    }, {
        'url': 'https://aeon.co/videos/chew-over-the-prisoners-dilemma-and-see-if-you-can-find-the-rational-path-out',
        'md5': '1cfda0bf3ae24df17d00f2c0cb6cc21b',
        'info_dict': {
            'id': 'emyi4z-O0ls',
            'ext': 'mp4',
            'title': 'How to outsmart the Prisoner’s Dilemma - Lucas Husted',
            'thumbnail': 'https://i.ytimg.com/vi_webp/emyi4z-O0ls/maxresdefault.webp',
            'uploader': 'TED-Ed',
            'uploader_id': '@TEDEd',
            'uploader_url': 'https://www.youtube.com/@TEDEd',
            'duration': 344,
            'upload_date': '20200827',
            'channel_id': 'UCsooa4yRKGN_zEE8iknghZA',
            'playable_in_embed': True,
            'description': 'md5:c0959524f08cb60f96fd010f3dfb17f3',
            'categories': ['Education'],
            'like_count': int,
            'channel': 'TED-Ed',
            'chapters': 'count:7',
            'channel_url': 'https://www.youtube.com/channel/UCsooa4yRKGN_zEE8iknghZA',
            'tags': 'count:26',
            'availability': 'public',
            'channel_follower_count': int,
            'view_count': int,
            'age_limit': 0,
            'live_status': 'not_live',
            'comment_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        embed_url = traverse_obj(self._yield_json_ld(webpage, video_id), (
            lambda _, v: v['@type'] == 'VideoObject', 'embedUrl', {url_or_none}), get_all=False)
        if not embed_url:
            raise ExtractorError('No embed URL found in webpage')
        if 'player.vimeo.com' in embed_url:
            embed_url = VimeoIE._smuggle_referrer(embed_url, 'https://aeon.co/')
        return self.url_result(embed_url)
