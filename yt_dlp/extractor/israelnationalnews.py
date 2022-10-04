from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class IsraelNationalNewsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?israelnationalnews\.com/news/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.israelnationalnews.com/news/354520',
        'info_dict': {
            'id': '354520'
        },
        'playlist': [{
            'info_dict': {
                'id': 'jA84wQhVvg8',
                'title': 'Even CNN Host Is Shocked by How Bad Biden\'s Approval Ratings Have Gotten | DM CLIPS | Rubin Report',
                'ext': 'mp4',
                'description': 'md5:b7325a3d00c7596337dc3ae37e32d35c',
                'channel': 'The Rubin Report',
                'channel_follower_count': int,
                'comment_count': int,
                'categories': ['News & Politics'],
                'like_count': int,
                'uploader_url': 'http://www.youtube.com/user/RubinReport',
                'uploader_id': 'RubinReport',
                'availability': 'public',
                'view_count': int,
                'duration': 240,
                'thumbnail': 'https://i.ytimg.com/vi_webp/jA84wQhVvg8/maxresdefault.webp',
                'live_status': 'not_live',
                'playable_in_embed': True,
                'age_limit': 0,
                'tags': 'count:29',
                'channel_id': 'UCJdKr0Bgd_5saZYqLCa9mng',
                'channel_url': 'https://www.youtube.com/channel/UCJdKr0Bgd_5saZYqLCa9mng',
                'upload_date': '20220606',
                'uploader': 'The Rubin Report',
            }
        }]
    }]

    def _real_extract(self, url):
        news_article_id = self._match_id(url)
        article_json = self._download_json(
            f'https://www.israelnationalnews.com/Generic/NewAPI/Item?type=0&Item={news_article_id}', news_article_id)

        urls = traverse_obj(article_json, ('Content2', ..., 'content', ..., 'attrs', 'src'))
        if not urls:
            raise ExtractorError('This article does not have any videos', expected=True)

        return self.playlist_from_matches(urls, news_article_id, ie='Youtube')
