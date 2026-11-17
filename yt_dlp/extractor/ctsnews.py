from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import unified_timestamp


class CtsNewsIE(InfoExtractor):
    IE_DESC = '華視新聞'
    _VALID_URL = r'https?://news\.cts\.com\.tw/[a-z]+/[a-z]+/\d+/(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'http://news.cts.com.tw/cts/international/201501/201501291578109.html',
        'md5': 'a9875cb790252b08431186d741beaabe',
        'info_dict': {
            'id': '201501291578109',
            'ext': 'mp4',
            'title': '以色列.真主黨交火 3人死亡 - 華視新聞網',
            'description': '以色列和黎巴嫩真主黨，爆發五年最嚴重衝突，雙方砲轟交火，兩名以軍死亡，還有一名西班牙籍的聯合國維和人員也不幸罹難。大陸陝西、河南、安徽、江蘇和湖北五個省份出現大暴雪，嚴重影響陸空交通，不過九華山卻出現...',
            'timestamp': 1422528540,
            'upload_date': '20150129',
        },
    }, {
        # News count not appear on page but still available in database
        'url': 'http://news.cts.com.tw/cts/international/201309/201309031304098.html',
        'md5': '3aee7e0df7cdff94e43581f54c22619e',
        'info_dict': {
            'id': '201309031304098',
            'ext': 'mp4',
            'title': '韓國31歲童顏男 貌如十多歲小孩 - 華視新聞網',
            'description': '越有年紀的人，越希望看起來年輕一點，而南韓卻有一位31歲的男子，看起來像是11、12歲的小孩，身...',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1378205880,
            'upload_date': '20130903',
        },
    }, {
        # With Youtube embedded video
        'url': 'http://news.cts.com.tw/cts/money/201501/201501291578003.html',
        'md5': 'e4726b2ccd70ba2c319865e28f0a91d1',
        'info_dict': {
            'id': 'OVbfO7d0_hQ',
            'ext': 'mp4',
            'title': 'iPhone6熱銷 蘋果財報亮眼',
            'description': 'md5:f395d4f485487bb0f992ed2c4b07aa7d',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20150128',
            'uploader_id': 'TBSCTS',
            'uploader': '中華電視公司',
        },
        'add_ie': ['Youtube'],
    }]

    def _real_extract(self, url):
        news_id = self._match_id(url)
        page = self._download_webpage(url, news_id)

        news_id = self._hidden_inputs(page).get('get_id')

        if news_id:
            mp4_feed = self._download_json(
                'http://news.cts.com.tw/action/test_mp4feed.php',
                news_id, note='Fetching feed', query={'news_id': news_id})
            video_url = mp4_feed['source_url']
        else:
            self.to_screen('Not CTSPlayer video, trying Youtube...')
            youtube_url = YoutubeIE._extract_url(page)

            return self.url_result(youtube_url, ie='Youtube')

        description = self._html_search_meta('description', page)
        title = self._html_search_meta('title', page, fatal=True)
        thumbnail = self._html_search_meta('image', page)

        datetime_str = self._html_search_regex(
            r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2})', page, 'date and time', fatal=False)
        timestamp = None
        if datetime_str:
            timestamp = unified_timestamp(datetime_str) - 8 * 3600

        return {
            'id': news_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
        }
