from .common import InfoExtractor


class PixabayBaseIE(InfoExtractor):
    # Cookie header is required for the webpage request or it will 403
    _headers = {
        'Cookie': 'is_human=1;',
    }

    def _get_info(self, url, video_id, object_type):
        webpage = self._download_webpage(url, video_id, headers=self._headers)
        return self._search_json_ld(webpage, video_id, expected_type=object_type)


class PixabaySoundMusicIE(PixabayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?pixabay\.com/(?:music|sound-effects)/(?:[^/?#]+-)?(?P<id>\d+)'
    _TESTS = [
        # Music
        {
            'url': 'https://pixabay.com/music/future-bass-no-copyright-music-537751/',
            'info_dict': {
                'id': '537751',
                'ext': 'mp3',
                'title': 'No Copyright Music by SigmaMusicArt | Royalty-free Music',
                'description': 'md5:08944ea4deb3e7eb34dee808ac6435e8',
                'view_count': int,
                'thumbnail': r're:^https?://.*\.(?:png|jpg)',
                'uploader': 'SigmaMusicArt',
                'like_count': int,
                'duration': 123,
                'tags': 'count:25',
                'timestamp': 1780641648,
                'upload_date': '20260605',
            },
        },
        # Sound Effect
        {
            'url': 'https://pixabay.com/sound-effects/film-special-effects-calm-inspiring-technology-logo-short-version-518993/',
            'info_dict': {
                'id': '518993',
                'ext': 'mp3',
                'title': 'Calm Inspiring Technology Logo (Short Version) by AleXZavesa | Royalty-free Sound Effects',
                'description': 'md5:5e204546f9e1ecab45ecb8638799866a',
                'view_count': int,
                'thumbnail': r're:^https?://.*\.(?:png|jpg)',
                'uploader': 'AleXZavesa',
                'like_count': int,
                'duration': 11,
                'tags': 'count:24',
                'timestamp': 1776145411,
                'upload_date': '20260414',
            },
        },
        # Sound Effect - no thumbnail
        {
            'url': 'https://pixabay.com/sound-effects/musical-relaxing-guitar-loop-v5-245859/',
            'info_dict': {
                'id': '245859',
                'ext': 'mp3',
                'title': 'Relaxing Guitar Loop V5 by IdoBerg | Royalty-free Sound Effects',
                'description': 'md5:78ebfcb0a317d39f69084e4f71715114',
                'view_count': int,
                'uploader': 'IdoBerg',
                'like_count': int,
                'duration': 18,
                'tags': 'count:14',
                'timestamp': 1727680678,
                'upload_date': '20240930',
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
            'title': 'Geothermal, Iceland, Nature. Free Stock Video',
            'description': 'md5:dada78660f78efbb23daf7e4a7ccb90a',
            'view_count': int,
            'thumbnail': r're:^https?://.*\.(?:png|jpg)',
            'uploader': 'Gylfi',
            'like_count': int,
            'duration': 22,
            'tags': 'count:17',
            'timestamp': 1776896755,
            'upload_date': '20260422',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._get_info(url, video_id, 'VideoObject')

        return {
            'id': video_id,
            **info,
        }
