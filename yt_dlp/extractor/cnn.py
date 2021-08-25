from __future__ import unicode_literals


from .common import InfoExtractor
from .turner import TurnerBaseIE
from ..utils import url_basename


class CNNIE(TurnerBaseIE):
    _VALID_URL = r'''(?x)https?://(?:(?P<sub_domain>edition|www|money)\.)?cnn\.com/(?:video/(?:data/.+?|\?)/)?videos?/
        (?P<path>.+?/(?P<title>[^/]+?)(?:\.(?:[a-z\-]+)|(?=&)))'''

    _TESTS = [{
        'url': 'http://edition.cnn.com/video/?/video/sports/2013/06/09/nadal-1-on-1.cnn',
        'md5': '3e6121ea48df7e2259fe73a0628605c4',
        'info_dict': {
            'id': 'sports/2013/06/09/nadal-1-on-1.cnn',
            'ext': 'mp4',
            'title': 'Nadal wins 8th French Open title',
            'description': 'World Sport\'s Amanda Davies chats with 2013 French Open champion Rafael Nadal.',
            'duration': 135,
            'upload_date': '20130609',
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'http://edition.cnn.com/video/?/video/us/2013/08/21/sot-student-gives-epic-speech.georgia-institute-of-technology&utm_source=feedburner&utm_medium=feed&utm_campaign=Feed%3A+rss%2Fcnn_topstories+%28RSS%3A+Top+Stories%29',
        'md5': 'b5cc60c60a3477d185af8f19a2a26f4e',
        'info_dict': {
            'id': 'us/2013/08/21/sot-student-gives-epic-speech.georgia-institute-of-technology',
            'ext': 'mp4',
            'title': "Student's epic speech stuns new freshmen",
            'description': "A Georgia Tech student welcomes the incoming freshmen with an epic speech backed by music from \"2001: A Space Odyssey.\"",
            'upload_date': '20130821',
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'http://www.cnn.com/video/data/2.0/video/living/2014/12/22/growing-america-nashville-salemtown-board-episode-1.hln.html',
        'md5': 'f14d02ebd264df951feb2400e2c25a1b',
        'info_dict': {
            'id': 'living/2014/12/22/growing-america-nashville-salemtown-board-episode-1.hln',
            'ext': 'mp4',
            'title': 'Nashville Ep. 1: Hand crafted skateboards',
            'description': 'md5:e7223a503315c9f150acac52e76de086',
            'upload_date': '20141222',
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'http://money.cnn.com/video/news/2016/08/19/netflix-stunning-stats.cnnmoney/index.html',
        'md5': '52a515dc1b0f001cd82e4ceda32be9d1',
        'info_dict': {
            'id': '/video/news/2016/08/19/netflix-stunning-stats.cnnmoney',
            'ext': 'mp4',
            'title': '5 stunning stats about Netflix',
            'description': 'Did you know that Netflix has more than 80 million members? Here are five facts about the online video distributor that you probably didn\'t know.',
            'upload_date': '20160819',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://cnn.com/video/?/video/politics/2015/03/27/pkg-arizona-senator-church-attendance-mandatory.ktvk',
        'only_matching': True,
    }, {
        'url': 'http://cnn.com/video/?/video/us/2015/04/06/dnt-baker-refuses-anti-gay-order.wkmg',
        'only_matching': True,
    }, {
        'url': 'http://edition.cnn.com/videos/arts/2016/04/21/olympic-games-cultural-a-z-brazil.cnn',
        'only_matching': True,
    }]

    _CONFIG = {
        # http://edition.cnn.com/.element/apps/cvp/3.0/cfg/spider/cnn/expansion/config.xml
        'edition': {
            'data_src': 'http://edition.cnn.com/video/data/3.0/video/%s/index.xml',
            'media_src': 'http://pmd.cdn.turner.com/cnn/big',
        },
        # http://money.cnn.com/.element/apps/cvp2/cfg/config.xml
        'money': {
            'data_src': 'http://money.cnn.com/video/data/4.0/video/%s.xml',
            'media_src': 'http://ht3.cdn.turner.com/money/big',
        },
    }

    def _extract_timestamp(self, video_data):
        # TODO: fix timestamp extraction
        return None

    def _real_extract(self, url):
        sub_domain, path, page_title = self._match_valid_url(url).groups()
        if sub_domain not in ('money', 'edition'):
            sub_domain = 'edition'
        config = self._CONFIG[sub_domain]
        return self._extract_cvp_info(
            config['data_src'] % path, page_title, {
                'default': {
                    'media_src': config['media_src'],
                },
                'f4m': {
                    'host': 'cnn-vh.akamaihd.net',
                },
            })


class CNNBlogsIE(InfoExtractor):
    _VALID_URL = r'https?://[^\.]+\.blogs\.cnn\.com/.+'
    _TEST = {
        'url': 'http://reliablesources.blogs.cnn.com/2014/02/09/criminalizing-journalism/',
        'md5': '3e56f97b0b6ffb4b79f4ea0749551084',
        'info_dict': {
            'id': 'bestoftv/2014/02/09/criminalizing-journalism.cnn',
            'ext': 'mp4',
            'title': 'Criminalizing journalism?',
            'description': 'Glenn Greenwald responds to comments made this week on Capitol Hill that journalists could be criminal accessories.',
            'upload_date': '20140209',
        },
        'expected_warnings': ['Failed to download m3u8 information'],
        'add_ie': ['CNN'],
    }

    def _real_extract(self, url):
        webpage = self._download_webpage(url, url_basename(url))
        cnn_url = self._html_search_regex(r'data-url="(.+?)"', webpage, 'cnn url')
        return self.url_result(cnn_url, CNNIE.ie_key())


class CNNArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:edition|www)\.)?cnn\.com/(?!videos?/)'
    _TEST = {
        'url': 'http://www.cnn.com/2014/12/21/politics/obama-north-koreas-hack-not-war-but-cyber-vandalism/',
        'md5': '689034c2a3d9c6dc4aa72d65a81efd01',
        'info_dict': {
            'id': 'bestoftv/2014/12/21/ip-north-korea-obama.cnn',
            'ext': 'mp4',
            'title': 'Obama: Cyberattack not an act of war',
            'description': 'md5:0a802a40d2376f60e6b04c8d5bcebc4b',
            'upload_date': '20141221',
        },
        'expected_warnings': ['Failed to download m3u8 information'],
        'add_ie': ['CNN'],
    }

    def _real_extract(self, url):
        webpage = self._download_webpage(url, url_basename(url))
        cnn_url = self._html_search_regex(r"video:\s*'([^']+)'", webpage, 'cnn url')
        return self.url_result('http://cnn.com/video/?/video/' + cnn_url, CNNIE.ie_key())
