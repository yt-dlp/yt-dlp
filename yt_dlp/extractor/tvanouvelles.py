import re

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor


class TVANouvellesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tvanouvelles\.ca/videos/(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.tvanouvelles.ca/videos/5117035533001',
        'info_dict': {
            'id': '5117035533001',
            'ext': 'mp4',
            'title': 'L’industrie du taxi dénonce l’entente entre Québec et Uber: explications',
            'description': 'md5:479653b7c8cf115747bf5118066bd8b3',
            'uploader_id': '1741764581',
            'timestamp': 1473352030,
            'upload_date': '20160908',
        },
        'add_ie': ['BrightcoveNew'],
    }
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/1741764581/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        brightcove_id = self._match_id(url)
        return self.url_result(
            self.BRIGHTCOVE_URL_TEMPLATE % brightcove_id,
            BrightcoveNewIE.ie_key(), brightcove_id)


class TVANouvellesArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tvanouvelles\.ca/(?:[^/]+/)+(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'http://www.tvanouvelles.ca/2016/11/17/des-policiers-qui-ont-la-meche-un-peu-courte',
        'info_dict': {
            'id': 'des-policiers-qui-ont-la-meche-un-peu-courte',
            'title': 'Des policiers qui ont «la mèche un peu courte»?',
            'description': 'md5:92d363c8eb0f0f030de9a4a84a90a3a0',
        },
        'playlist_mincount': 4,
    }

    @classmethod
    def suitable(cls, url):
        return False if TVANouvellesIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        entries = [
            self.url_result(
                'http://www.tvanouvelles.ca/videos/{}'.format(mobj.group('id')),
                ie=TVANouvellesIE.ie_key(), video_id=mobj.group('id'))
            for mobj in re.finditer(
                r'data-video-id=(["\'])?(?P<id>\d+)', webpage)]

        title = self._og_search_title(webpage, fatal=False)
        description = self._og_search_description(webpage)

        return self.playlist_result(entries, display_id, title, description)
