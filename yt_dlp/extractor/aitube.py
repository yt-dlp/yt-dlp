from .common import InfoExtractor
from ..utils import int_or_none, merge_dicts


class AitubeKZVideoIE(InfoExtractor):
    _VALID_URL = r'https?://aitube\.kz/(?:video|embed/)\?(?:[^\?]+)?id=(?P<id>[\w-]+)'
    _TESTS = [{
        # id paramater as first parameter
        'url': 'https://aitube.kz/video?id=9291d29b-c038-49a1-ad42-3da2051d353c&playlistId=d55b1f5f-ef2a-4f23-b646-2a86275b86b7&season=1',
        'info_dict': {
            'id': '9291d29b-c038-49a1-ad42-3da2051d353c',
            'ext': 'mp4',
            'duration': 2174.0,
            'channel_id': '94962f73-013b-432c-8853-1bd78ca860fe',
            'like_count': int,
            'channel': 'ASTANA TV',
            'comment_count': int,
            'view_count': int,
            'description': 'Смотреть любимые сериалы и видео, поделиться видео и сериалами с друзьями и близкими',
            'thumbnail': 'https://cdn.static02.aitube.kz/kz.aitudala.aitube.staticaccess/files/ddf2a2ff-bee3-409b-b5f2-2a8202bba75b',
            'upload_date': '20221102',
            'timestamp': 1667370519,
            'title': 'Ангел хранитель 1 серия',
            'channel_follower_count': int,
        },
    }, {
        # embed url
        'url': 'https://aitube.kz/embed/?id=9291d29b-c038-49a1-ad42-3da2051d353c',
        'only_matching': True,
    }, {
        # id parameter is not as first paramater
        'url': 'https://aitube.kz/video?season=1&id=9291d29b-c038-49a1-ad42-3da2051d353c&playlistId=d55b1f5f-ef2a-4f23-b646-2a86275b86b7',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        nextjs_data = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['videoInfo']
        json_ld_data = self._search_json_ld(webpage, video_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://api-http.aitube.kz/kz.aitudala.aitube.staticaccess/video/{video_id}/video', video_id)

        return merge_dicts({
            'id': video_id,
            'title': nextjs_data.get('title') or self._html_search_meta(['name', 'og:title'], webpage),
            'description': nextjs_data.get('description'),
            'formats': formats,
            'subtitles': subtitles,
            'view_count': (nextjs_data.get('viewCount')
                           or int_or_none(self._html_search_meta('ya:ovs:views_total', webpage))),
            'like_count': nextjs_data.get('likeCount'),
            'channel': nextjs_data.get('channelTitle'),
            'channel_id': nextjs_data.get('channelId'),
            'thumbnail': nextjs_data.get('coverUrl'),
            'comment_count': nextjs_data.get('commentCount'),
            'channel_follower_count': int_or_none(nextjs_data.get('channelSubscriberCount')),
        }, json_ld_data)
