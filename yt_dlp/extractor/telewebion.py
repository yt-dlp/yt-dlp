from .common import InfoExtractor


class TelewebionIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?telewebion\.com/#!/episode/(?P<id>\d+)'

    _TEST = {
        'url': 'http://www.telewebion.com/#!/episode/1263668/',
        'info_dict': {
            'id': '1263668',
            'ext': 'mp4',
            'title': 'قرعه\u200cکشی لیگ قهرمانان اروپا',
            'thumbnail': r're:^https?://.*\.jpg',
            'view_count': int,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        secure_token = self._download_webpage(
            'http://m.s2.telewebion.com/op/op?action=getSecurityToken', video_id)
        episode_details = self._download_json(
            'http://m.s2.telewebion.com/op/op', video_id,
            query={'action': 'getEpisodeDetails', 'episode_id': video_id})

        m3u8_url = 'http://m.s1.telewebion.com/smil/%s.m3u8?filepath=%s&m3u8=1&secure_token=%s' % (
            video_id, episode_details['file_path'], secure_token)
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, ext='mp4', m3u8_id='hls')

        picture_paths = [
            episode_details.get('picture_path'),
            episode_details.get('large_picture_path'),
        ]

        thumbnails = [{
            'url': picture_path,
            'preference': idx,
        } for idx, picture_path in enumerate(picture_paths) if picture_path is not None]

        return {
            'id': video_id,
            'title': episode_details['title'],
            'formats': formats,
            'thumbnails': thumbnails,
            'view_count': episode_details.get('view_count'),
        }
