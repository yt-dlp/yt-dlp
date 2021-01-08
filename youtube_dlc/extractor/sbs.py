# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    smuggle_url,
    ExtractorError,
)


class SBSIE(InfoExtractor):
    IE_DESC = 'sbs.com.au'
    _VALID_URL = r'https?://(?:www\.)?sbs\.com\.au/(?:ondemand(?:/video/(?:single/)?|.*?\bplay=)|news/(?:embeds/)?video/)(?P<id>[0-9]+)'

    _TESTS = [{
        # Original URL is handled by the generic IE which finds the iframe:
        # http://www.sbs.com.au/thefeed/blog/2014/08/21/dingo-conservation
        'url': 'http://www.sbs.com.au/ondemand/video/single/320403011771/?source=drupal&vertical=thefeed',
        'md5': '3150cf278965eeabb5b4cea1c963fe0a',
        'info_dict': {
            'id': '_rFBPRPO4pMR',
            'ext': 'mp4',
            'title': 'Dingo Conservation (The Feed)',
            'description': 'md5:f250a9856fca50d22dec0b5b8015f8a5',
            'thumbnail': r're:http://.*\.jpg',
            'duration': 308,
            'timestamp': 1408613220,
            'upload_date': '20140821',
            'uploader': 'SBSC',
        },
    }, {
        'url': 'http://www.sbs.com.au/ondemand/video/320403011771/Dingo-Conservation-The-Feed',
        'only_matching': True,
    }, {
        'url': 'http://www.sbs.com.au/news/video/471395907773/The-Feed-July-9',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/?play=1836638787723',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/program/inside-windsor-castle?play=1283505731842',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/news/embeds/video/1840778819866',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        player_params = self._download_json(
            'http://www.sbs.com.au/api/video_pdkvars/id/%s?form=json' % video_id, video_id)

        error = player_params.get('error')
        if error:
            error_message = 'Sorry, The video you are looking for does not exist.'
            video_data = error.get('results') or {}
            error_code = error.get('errorCode')
            if error_code == 'ComingSoon':
                error_message = '%s is not yet available.' % video_data.get('title', '')
            elif error_code in ('Forbidden', 'intranetAccessOnly'):
                error_message = 'Sorry, This video cannot be accessed via this website'
            elif error_code == 'Expired':
                error_message = 'Sorry, %s is no longer available.' % video_data.get('title', '')
            raise ExtractorError('%s said: %s' % (self.IE_NAME, error_message), expected=True)

        urls = player_params['releaseUrls']
        theplatform_url = (urls.get('progressive') or urls.get('html')
                           or urls.get('standard') or player_params['relatedItemsURL'])

        return {
            '_type': 'url_transparent',
            'ie_key': 'ThePlatform',
            'id': video_id,
            'url': smuggle_url(self._proto_relative_url(theplatform_url), {'force_smil_url': True}),
        }
