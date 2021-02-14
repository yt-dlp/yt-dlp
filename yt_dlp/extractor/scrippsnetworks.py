# coding: utf-8
from __future__ import unicode_literals

import json
import hashlib
import re

from .aws import AWSIE
from .anvato import AnvatoIE
from .common import InfoExtractor
from ..utils import (
    smuggle_url,
    urlencode_postdata,
    xpath_text,
)


class ScrippsNetworksWatchIE(AWSIE):
    IE_NAME = 'scrippsnetworks:watch'
    _VALID_URL = r'''(?x)
                    https?://
                        watch\.
                        (?P<site>geniuskitchen)\.com/
                        (?:
                            player\.[A-Z0-9]+\.html\#|
                            show/(?:[^/]+/){2}|
                            player/
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'http://watch.geniuskitchen.com/player/3787617/Ample-Hills-Ice-Cream-Bike/',
        'info_dict': {
            'id': '4194875',
            'ext': 'mp4',
            'title': 'Ample Hills Ice Cream Bike',
            'description': 'Courtney Rada churns up a signature GK Now ice cream with The Scoopmaster.',
            'uploader': 'ANV',
            'upload_date': '20171011',
            'timestamp': 1507698000,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [AnvatoIE.ie_key()],
    }]

    _SNI_TABLE = {
        'geniuskitchen': 'genius',
    }

    _AWS_API_KEY = 'E7wSQmq0qK6xPrF13WmzKiHo4BQ7tip4pQcSXVl1'
    _AWS_PROXY_HOST = 'web.api.video.snidigital.com'

    _AWS_USER_AGENT = 'aws-sdk-js/2.80.0 callback'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        site_id, video_id = mobj.group('site', 'id')

        aws_identity_id_json = json.dumps({
            'IdentityId': '%s:7655847c-0ae7-4d9b-80d6-56c062927eb3' % self._AWS_REGION
        }).encode('utf-8')
        token = self._download_json(
            'https://cognito-identity.%s.amazonaws.com/' % self._AWS_REGION, video_id,
            data=aws_identity_id_json,
            headers={
                'Accept': '*/*',
                'Content-Type': 'application/x-amz-json-1.1',
                'Referer': url,
                'X-Amz-Content-Sha256': hashlib.sha256(aws_identity_id_json).hexdigest(),
                'X-Amz-Target': 'AWSCognitoIdentityService.GetOpenIdToken',
                'X-Amz-User-Agent': self._AWS_USER_AGENT,
            })['Token']

        sts = self._download_xml(
            'https://sts.amazonaws.com/', video_id, data=urlencode_postdata({
                'Action': 'AssumeRoleWithWebIdentity',
                'RoleArn': 'arn:aws:iam::710330595350:role/Cognito_WebAPIUnauth_Role',
                'RoleSessionName': 'web-identity',
                'Version': '2011-06-15',
                'WebIdentityToken': token,
            }), headers={
                'Referer': url,
                'X-Amz-User-Agent': self._AWS_USER_AGENT,
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            })

        def get(key):
            return xpath_text(
                sts, './/{https://sts.amazonaws.com/doc/2011-06-15/}%s' % key,
                fatal=True)

        mcp_id = self._aws_execute_api({
            'uri': '/1/web/brands/%s/episodes/scrid/%s' % (self._SNI_TABLE[site_id], video_id),
            'access_key': get('AccessKeyId'),
            'secret_key': get('SecretAccessKey'),
            'session_token': get('SessionToken'),
        }, video_id)['results'][0]['mcpId']

        return self.url_result(
            smuggle_url(
                'anvato:anvato_scripps_app_web_prod_0837996dbe373629133857ae9eb72e740424d80a:%s' % mcp_id,
                {'geo_countries': ['US']}),
            AnvatoIE.ie_key(), video_id=mcp_id)


class ScrippsNetworksIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?P<site>cookingchanneltv|discovery|(?:diy|food)network|hgtv|travelchannel)\.com/videos/[0-9a-z-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.cookingchanneltv.com/videos/the-best-of-the-best-0260338',
        'info_dict': {
            'id': '0260338',
            'ext': 'mp4',
            'title': 'The Best of the Best',
            'description': 'Catch a new episode of MasterChef Canada Tuedsay at 9/8c.',
            'timestamp': 1475678834,
            'upload_date': '20161005',
            'uploader': 'SCNI-SCND',
        },
        'add_ie': ['ThePlatform'],
    }, {
        'url': 'https://www.diynetwork.com/videos/diy-barnwood-tablet-stand-0265790',
        'only_matching': True,
    }, {
        'url': 'https://www.foodnetwork.com/videos/chocolate-strawberry-cake-roll-7524591',
        'only_matching': True,
    }, {
        'url': 'https://www.hgtv.com/videos/cookie-decorating-101-0301929',
        'only_matching': True,
    }, {
        'url': 'https://www.travelchannel.com/videos/two-climates-one-bag-5302184',
        'only_matching': True,
    }, {
        'url': 'https://www.discovery.com/videos/guardians-of-the-glades-cooking-with-tom-cobb-5578368',
        'only_matching': True,
    }]
    _ACCOUNT_MAP = {
        'cookingchanneltv': 2433005105,
        'discovery': 2706091867,
        'diynetwork': 2433004575,
        'foodnetwork': 2433005105,
        'hgtv': 2433004575,
        'travelchannel': 2433005739,
    }
    _TP_TEMPL = 'https://link.theplatform.com/s/ip77QC/media/guid/%d/%s?mbr=true'

    def _real_extract(self, url):
        site, guid = re.match(self._VALID_URL, url).groups()
        return self.url_result(smuggle_url(
            self._TP_TEMPL % (self._ACCOUNT_MAP[site], guid),
            {'force_smil_url': True}), 'ThePlatform', guid)
