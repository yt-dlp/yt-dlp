from .common import InfoExtractor
from .dailymotion import DailymotionIE
from .youtube import YoutubeIE


class GMANetworkVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www)\.gmanetwork\.com/(?:\w+/){3}(?P<id>\d+)/(?P<display_id>[\w-]+)/video'
    _TESTS = [{
        'url': 'https://www.gmanetwork.com/fullepisodes/home/running_man_philippines/168677/running-man-philippines-catch-the-thief-full-chapter-2/video?section=home',
        'info_dict': {
            'id': '28BqW0AXPe0',
            'ext': 'mp4',
            'upload_date': '20220919',
            'uploader_url': 'http://www.youtube.com/channel/UChsoPNR5x-wdSO2GrOSIWqQ',
            'like_count': int,
            'view_count': int,
            'uploader': 'YoüLOL',
            'channel_id': 'UChsoPNR5x-wdSO2GrOSIWqQ',
            'duration': 5313,
            'comment_count': int,
            'tags': 'count:22',
            'uploader_id': 'UChsoPNR5x-wdSO2GrOSIWqQ',
            'title': 'Running Man Philippines: Catch the Thief (FULL CHAPTER 2)',
            'channel_url': 'https://www.youtube.com/channel/UChsoPNR5x-wdSO2GrOSIWqQ',
            'thumbnail': 'https://i.ytimg.com/vi/28BqW0AXPe0/maxresdefault.jpg',
            'release_timestamp': 1663594212,
            'age_limit': 0,
            'channel_follower_count': int,
            'categories': ['Entertainment'],
            'description': 'md5:811bdcea74f9c48051824e494756e926',
            'live_status': 'not_live',
            'playable_in_embed': True,
            'channel': 'YoüLOL',
            'availability': 'public',
            'release_date': '20220919',
        }
    }, {
        'url': 'https://www.gmanetwork.com/fullepisodes/home/more_than_words/87059/more-than-words-full-episode-80/video?section=home',
        'info_dict': {
            'id': 'yiDOExw2aSA',
            'ext': 'mp4',
            'live_status': 'not_live',
            'channel': 'GMANetwork',
            'like_count': int,
            'channel_follower_count': int,
            'description': 'md5:6d00cd658394fa1a5071200d3ed4be05',
            'duration': 1419,
            'age_limit': 0,
            'comment_count': int,
            'upload_date': '20181003',
            'thumbnail': 'https://i.ytimg.com/vi_webp/yiDOExw2aSA/maxresdefault.webp',
            'availability': 'public',
            'playable_in_embed': True,
            'channel_id': 'UCKL5hAuzgFQsyrsQKgU0Qng',
            'title': 'More Than Words: Full Episode 80 (Finale)',
            'uploader_id': 'GMANETWORK',
            'categories': ['Entertainment'],
            'uploader': 'GMANetwork',
            'channel_url': 'https://www.youtube.com/channel/UCKL5hAuzgFQsyrsQKgU0Qng',
            'tags': 'count:29',
            'view_count': int,
            'uploader_url': 'http://www.youtube.com/user/GMANETWORK',
        }
    }]

    def _real_extract(self, url):
        content_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        webpage = self._download_webpage(url, display_id)
        # webpage route
        youtube_id = self._search_regex(
            r'var\s*YOUTUBE_VIDEO\s*=\s*[\'"]+(?P<yt_id>[\w-]+)', webpage, 'youtube_id', fatal=False)
        if youtube_id:
            return self.url_result(youtube_id, YoutubeIE, youtube_id)

        # api call route
        # more info at https://aphrodite.gmanetwork.com/fullepisodes/assets/fullepisodes/js/dist/fullepisodes_video.js?v=1.1.11
        network_url = self._search_regex(
            r'NETWORK_URL\s*=\s*[\'"](?P<url>[^\'"]+)', webpage, 'network_url')
        json_data = self._download_json(f'{network_url}api/data/content/video/{content_id}', display_id)
        if json_data.get('video_file'):
            return self.url_result(json_data['video_file'], YoutubeIE, json_data['video_file'])
        else:
            return self.url_result(json_data['dailymotion_file'], DailymotionIE, json_data['dailymotion_file'])
