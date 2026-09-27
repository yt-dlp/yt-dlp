from .common import InfoExtractor
from ..utils import url_or_none
from ..utils.traversal import traverse_obj


class PixabayBaseIE(InfoExtractor):
    # Cookie header is required for the webpage request or it will 403
    _headers = {
        'Cookie': 'is_human=1;',
    }

    def _get_info(self, url, video_id, object_type):
        webpage = self._download_webpage(url, video_id, headers=self._headers)
        info = self._search_json_ld(webpage, video_id, expected_type=object_type)

        return traverse_obj(info, {
            'url': ('url', {url_or_none}),
            'thumbnail': ('thumbnails', 0, 'url', {url_or_none}),
            'view_count': ('view_count', {int}),
            'description': ('description', {str}),
            'title': ('title', {str}),
        })


class PixabaySoundMusicIE(PixabayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?pixabay\.com/(?:music|sound-effects)/(?:[^/?#]+-)?(?P<id>\d+)'
    _TESTS = [
        # Music
        {
            'url': 'https://pixabay.com/music/future-bass-no-copyright-music-537751/',
            'info_dict': {
                'id': '537751',
                'ext': 'mp3',
                'thumbnail': r're:^https?://.*\.(?:png|jpg)',
                'view_count': int,
                'description': 'md5:08944ea4deb3e7eb34dee808ac6435e8',
                'title': 'No Copyright Music by SigmaMusicArt | Royalty-free Music',
            },
        },
        # Sound Effect
        {
            'url': 'https://pixabay.com/sound-effects/film-special-effects-calm-inspiring-technology-logo-short-version-518993/',
            'info_dict': {
                'id': '518993',
                'ext': 'mp3',
                'thumbnail': r're:^https?://.*\.(?:png|jpg)',
                'view_count': int,
                'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
                'title': 'Calm Inspiring Technology Logo (Short Version) by AleXZavesa | Royalty-free Music',
            },
        },
        # Sound Effect - no thumbnail
        {
            'url': 'https://pixabay.com/sound-effects/musical-relaxing-guitar-loop-v5-245859/',
            'info_dict': {
                'id': '245859',
                'ext': 'mp3',
                'view_count': int,
                'description': 'md5:a0ef48a42a6f1bb534b8478f4ca602eb',
                'title': 'Relaxing Guitar Loop V5 by IdoBerg | Royalty-free Music',
            },
        }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._get_info(url, video_id, 'AudioObject')

        return {
            'id': video_id,
            'vcodec': 'none',
            **info,
        }


class PixabayVideosIE(PixabayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?pixabay\.com/videos/(?:[^/?#]+-)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://pixabay.com/videos/geothermal-iceland-nature-steam-348057/',
        'info_dict': {
            'id': '348057',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.(?:png|jpg)',
            'view_count': int,
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'title': 'Geothermal, Iceland, Nature. Free Stock Video',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._get_info(url, video_id, 'VideoObject')

        return {
            'id': video_id,
            **info,
        }
