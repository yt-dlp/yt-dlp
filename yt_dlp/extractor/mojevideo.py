from .common import InfoExtractor
from ..utils import js_to_json, remove_end


class MojevideoIE(InfoExtractor):
    IE_DESC = 'mojevideo.sk'
    _VALID_URL = r'https?://(?:www\.)?mojevideo\.sk/video/(?P<id>\w+)/(?P<display_id>\w+?)\.html'

    _TESTS = [{
        'url': 'https://www.mojevideo.sk/video/3d17c/chlapci_dobetonovali_sme_mame_hotovo.html',
        'md5': '384a4628bd2bbd261c5206cf77c38c17',
        'info_dict': {
            'id': '250236',
            'ext': 'mp4',
            'title': 'Chlapci dobetónovali sme, máme hotovo!',
            'display_id': 'chlapci_dobetonovali_sme_mame_hotovo',
            'description': 'md5:a0822126044050d304a9ef58c92ddb34',
            'thumbnail': 'https://fs5.mojevideo.sk/imgfb/250236.jpg',
            'duration': 21.0,
            'upload_date': '20230919',
            'timestamp': 1695129706,
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'comment_count': int,
        },
    }, {
        'url': 'https://www.mojevideo.sk/video/14677/den_blbec.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        page_id, display_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, page_id)

        video_id = self._search_regex(r'\bvId\s*=\s*(\d+)', webpage, 'video id')
        video_exp = self._search_regex(r'\bvEx\s*=\s*["\'](\d+)', webpage, 'video expiry')
        video_hash = self._search_json(
            r'\bvHash\s*=\s*', webpage, 'video hash', video_id,
            contains_pattern=r'\[.+\]', transform_source=js_to_json)[0]

        return {
            'id': video_id,
            'display_id': display_id,
            'url': f'https://cache01.mojevideo.sk/securevideos69/{video_id}.mp4?md5={video_hash}&expires={video_exp}',
            'title': self._og_search_title(webpage, default=None)
            or remove_end(self._html_extract_title(webpage, 'title'), ' - Mojevideo'),
            'description': self._og_search_description(webpage),
            **self._search_json_ld(webpage, video_id, default={}),
        }
