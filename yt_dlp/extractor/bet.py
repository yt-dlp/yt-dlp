from .mtv import MTVServicesInfoExtractor
from ..utils import unified_strdate

# TODO Remove - Reason: Outdated Site


class BetIE(MTVServicesInfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bet\.com/(?:[^/]+/)+(?P<id>.+?)\.html'
    _TESTS = [
        {
            'url': 'http://www.bet.com/news/politics/2014/12/08/in-bet-exclusive-obama-talks-race-and-racism.html',
            'info_dict': {
                'id': '07e96bd3-8850-3051-b856-271b457f0ab8',
                'display_id': 'in-bet-exclusive-obama-talks-race-and-racism',
                'ext': 'flv',
                'title': 'A Conversation With President Obama',
                'description': 'President Obama urges persistence in confronting racism and bias.',
                'duration': 1534,
                'upload_date': '20141208',
                'thumbnail': r're:(?i)^https?://.*\.jpg$',
                'subtitles': {
                    'en': 'mincount:2',
                }
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.bet.com/video/news/national/2014/justice-for-ferguson-a-community-reacts.html',
            'info_dict': {
                'id': '9f516bf1-7543-39c4-8076-dd441b459ba9',
                'display_id': 'justice-for-ferguson-a-community-reacts',
                'ext': 'flv',
                'title': 'Justice for Ferguson: A Community Reacts',
                'description': 'A BET News special.',
                'duration': 1696,
                'upload_date': '20141125',
                'thumbnail': r're:(?i)^https?://.*\.jpg$',
                'subtitles': {
                    'en': 'mincount:2',
                }
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        }
    ]

    _FEED_URL = "http://feeds.mtvnservices.com/od/feed/bet-mrss-player"

    def _get_feed_query(self, uri):
        return {
            'uuid': uri,
        }

    def _extract_mgid(self, webpage):
        return self._search_regex(r'data-uri="([^"]+)', webpage, 'mgid')

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)
        mgid = self._extract_mgid(webpage)
        videos_info = self._get_videos_info(mgid)

        info_dict = videos_info['entries'][0]

        upload_date = unified_strdate(self._html_search_meta('date', webpage))
        description = self._html_search_meta('description', webpage)

        info_dict.update({
            'display_id': display_id,
            'description': description,
            'upload_date': upload_date,
        })

        return info_dict
