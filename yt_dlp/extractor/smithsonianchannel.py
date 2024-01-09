from .mtv import MTVServicesInfoExtractor
from ..utils import (
    url_basename,
    try_get
)


class SmithsonianChannelIE(MTVServicesInfoExtractor):
    IE_NAME = 'smithsonianchannel.com'
    _FEED_URL = 'http://feeds.mtvnservices.com/od/feed/intl-mrss-player-feed'

    _TESTS = [{
        'url': 'https://www.smithsonianchannel.com/episodes/yj8m78/the-last-747-the-last-747-ep-1',
        'info_dict': {
            'title': 'The Last 747 ｜ HDSMNS143A eng ｜ Version： 1293774 ｜ Smithsonian S1',
            'description': "The Last 747 captures the emotion around the build of Boeing's last 747 jumbo jet and also tells the story of how this one airplane completely transformed the economics of air travel \u2013 with huge implications for globalization, trade and geopolitics",
            'duration': 667.0,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    _VALID_URL = r'https?://(?:www\.)?smithsonianchannel\.com/(?:special|episodes)/(?P<id>[^/?#.]+)'

    def _get_feed_query(self, uri):
        return {
            'arcEp': 'shared.smithsonian.us',
            'mgid': uri,
        }

    def _extract_mgid(self, webpage):
        data = self._parse_json(self._search_regex(r'__DATA__\s*=\s*({.+?});', webpage, 'data'), None)
        main_container = self._extract_child_with_type(data, 'MainContainer')
        specials_page = self._extract_child_with_type(main_container, 'PropertySpecialsPage')
        if specials_page:
            url = try_get(specials_page, lambda x: x['props']['headerProps']['details']['meta']['url'])
            if url is not None and url[0] == "/":
                url = 'https://www.smithsonianchannel.com/' + url
            title = url_basename(url)
            webpage = self._download_webpage(url, title)
            return super()._extract_mgid(webpage)
        else:
            return super()._extract_mgid(webpage)
