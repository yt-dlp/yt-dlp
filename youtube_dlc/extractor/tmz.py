# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class TMZIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tmz\.com/videos/.*(?P<id>[^/?#]{10,10})'
    _TESTS = [{
        'url': 'http://www.tmz.com/videos/0_okj015ty/',
        'md5': '4d22a51ef205b6c06395d8394f72d560',
        'info_dict': {
            'id': '0_okj015ty',
            'ext': 'mp4',
            'title': 'Kim Kardashian\'s Boobs Unlock a Mystery!',
            'timestamp': 1394747163,
            'uploader_id': 'batchUser',
            'upload_date': '20140313',
        }
    }, {
        'url': 'http://www.tmz.com/videos/0-cegprt2p/',
        'info_dict': {
            'id': '0_cegprt2p',
            'ext': 'mp4',
            'title': "No Charges Against Hillary Clinton? Harvey Says It Ain't Over Yet",
            'timestamp': 1467831837,
            'uploader_id': 'batchUser',
            'upload_date': '20160706',
        }
    }, {
        'url': 'https://www.tmz.com/videos/071119-chris-morgan-women-4590005-0-zcsejvcr/',
        'info_dict': {
            'id': '0_zcsejvcr',
            'ext': 'mxf',
            'title': "Angry Bagel Shop Guy Says He Doesn't Trust Women",
            'timestamp': 1562889485,
            'uploader_id': 'batchUser',
            'upload_date': '20190711',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).replace('-', '_')
        return self.url_result('kaltura:591531:%s' % video_id, 'Kaltura', video_id)


class TMZArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tmz\.com/\d{4}/\d{2}/\d{2}/(?P<id>[^/]+)/?'
    _TESTS = [{
        'url': 'http://www.tmz.com/2015/04/19/bobby-brown-bobbi-kristina-awake-video-concert',
        'md5': '5429c85db8bde39a473a56ca8c4c5602',
        'info_dict': {
            'id': '0_6snoelag',
            'ext': 'mp4',
            'title': 'Bobby Brown Tells Crowd ... Bobbi Kristina is Awake',
            'timestamp': 1429467813,
            'upload_date': '20150419',
            'uploader_id': 'batchUser',
        }
    }, {
        'url': 'http://www.tmz.com/2015/09/19/patti-labelle-concert-fan-stripping-kicked-out-nicki-minaj/',
        'info_dict': {
            'id': '0_jerz7s3l',
            'ext': 'mp4',
            'title': 'Patti LaBelle -- Goes Nuclear On Stripping Fan',
            'timestamp': 1442683746,
            'upload_date': '20150919',
            'uploader_id': 'batchUser',
        }
    }, {
        'url': 'http://www.tmz.com/2016/01/28/adam-silver-sting-drake-blake-griffin/',
        'info_dict': {
            'id': '0_ytz87kk7',
            'ext': 'mp4',
            'title': "NBA's Adam Silver -- Blake Griffin's a Great Guy ... He'll Learn from This",
            'timestamp': 1454010989,
            'upload_date': '20160128',
            'uploader_id': 'batchUser',
        }
    }, {
        'url': 'http://www.tmz.com/2016/10/27/donald-trump-star-vandal-arrested-james-otis/',
        'info_dict': {
            'id': '0_isigfatu',
            'ext': 'mp4',
            'title': "Trump Star Vandal -- I'm Not Afraid of Donald or the Cops!",
            'timestamp': 1477500095,
            'upload_date': '20161026',
            'uploader_id': 'batchUser',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        params = self._html_search_regex(r'TMZ.actions.clickLink\(([\s\S]+?)\)',
                                         webpage, 'embedded video info').split(',')
        new_url = params[0].strip("'\"")
        if new_url != url:
            return self.url_result(new_url)
