from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils import (
    sanitized_Request,
    urlencode_postdata,
)


class GDCVaultIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gdcvault\.com/play/(?P<id>\d+)(?:/(?P<name>[\w-]+))?'
    _NETRC_MACHINE = 'gdcvault'
    _TESTS = [
        {
            'url': 'http://www.gdcvault.com/play/1019721/Doki-Doki-Universe-Sweet-Simple',
            'md5': '7ce8388f544c88b7ac11c7ab1b593704',
            'info_dict': {
                'id': '201311826596_AWNY',
                'display_id': 'Doki-Doki-Universe-Sweet-Simple',
                'ext': 'mp4',
                'title': 'Doki-Doki Universe: Sweet, Simple and Genuine (GDC Next 10)'
            }
        },
        {
            'url': 'http://www.gdcvault.com/play/1015683/Embracing-the-Dark-Art-of',
            'info_dict': {
                'id': '201203272_1330951438328RSXR',
                'display_id': 'Embracing-the-Dark-Art-of',
                'ext': 'flv',
                'title': 'Embracing the Dark Art of Mathematical Modeling in AI'
            },
            'params': {
                'skip_download': True,  # Requires rtmpdump
            }
        },
        {
            'url': 'http://www.gdcvault.com/play/1015301/Thexder-Meets-Windows-95-or',
            'md5': 'a5eb77996ef82118afbbe8e48731b98e',
            'info_dict': {
                'id': '1015301',
                'display_id': 'Thexder-Meets-Windows-95-or',
                'ext': 'flv',
                'title': 'Thexder Meets Windows 95, or Writing Great Games in the Windows 95 Environment',
            },
            'skip': 'Requires login',
        },
        {
            'url': 'http://gdcvault.com/play/1020791/',
            'only_matching': True,
        },
        {
            # Hard-coded hostname
            'url': 'http://gdcvault.com/play/1023460/Tenacious-Design-and-The-Interface',
            'md5': 'a8efb6c31ed06ca8739294960b2dbabd',
            'info_dict': {
                'id': '840376_BQRC',
                'ext': 'mp4',
                'display_id': 'Tenacious-Design-and-The-Interface',
                'title': 'Tenacious Design and The Interface of \'Destiny\'',
            },
        },
        {
            # Multiple audios
            'url': 'http://www.gdcvault.com/play/1014631/Classic-Game-Postmortem-PAC',
            'info_dict': {
                'id': '12396_1299111843500GMPX',
                'ext': 'mp4',
                'title': 'How to Create a Good Game - From My Experience of Designing Pac-Man',
            },
            # 'params': {
            #     'skip_download': True,  # Requires rtmpdump
            #     'format': 'jp',  # The japanese audio
            # }
        },
        {
            # gdc-player.html
            'url': 'http://www.gdcvault.com/play/1435/An-American-engine-in-Tokyo',
            'info_dict': {
                'id': '9350_1238021887562UHXB',
                'display_id': 'An-American-engine-in-Tokyo',
                'ext': 'mp4',
                'title': 'An American Engine in Tokyo:/nThe collaboration of Epic Games and Square Enix/nFor THE LAST REMINANT',
            },
        },
        {
            # Kaltura Embed
            'url': 'https://www.gdcvault.com/play/1026180/Mastering-the-Apex-of-Scaling',
            'info_dict': {
                'id': '0_h1fg8j3p',
                'ext': 'mp4',
                'title': 'Mastering the Apex of Scaling Game Servers (Presented by Multiplay)',
                'timestamp': 1554401811,
                'upload_date': '20190404',
                'uploader_id': 'joe@blazestreaming.com',
            },
            'params': {
                'format': 'mp4-408',
            },
        },
    ]

    def _login(self, webpage_url, display_id):
        username, password = self._get_login_info()
        if username is None or password is None:
            self.report_warning('It looks like ' + webpage_url + ' requires a login. Try specifying a username and password and try again.')
            return None

        mobj = re.match(r'(?P<root_url>https?://.*?/).*', webpage_url)
        login_url = mobj.group('root_url') + 'api/login.php'
        logout_url = mobj.group('root_url') + 'logout'

        login_form = {
            'email': username,
            'password': password,
        }

        request = sanitized_Request(login_url, urlencode_postdata(login_form))
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        self._download_webpage(request, display_id, 'Logging in')
        webpage = self._download_webpage(webpage_url, display_id, 'Getting authenticated video page')
        self._download_webpage(logout_url, display_id, 'Logging out')

        return webpage

    def _real_extract(self, url):
        video_id, name = re.match(self._VALID_URL, url).groups()
        display_id = name or video_id

        webpage = self._download_webpage(url, display_id)

        title = self._html_search_regex(
            r'<td><strong>Session Name:?</strong></td>\s*<td>(.*?)</td>',
            webpage, 'title')

        PLAYER_REGEX = r'<iframe src=\"(?P<manifest_url>.*?)\".*?</iframe>'
        manifest_url = self._html_search_regex(
            PLAYER_REGEX, webpage, 'manifest_url')

        partner_id = self._search_regex(
            r'/p(?:artner_id)?/(\d+)', manifest_url, 'partner id',
            default='1670711')

        kaltura_id = self._search_regex(
            r'entry_id=(?P<id>(?:[^&])+)', manifest_url,
            'kaltura id', group='id')

        return {
            '_type': 'url_transparent',
            'url': 'kaltura:%s:%s' % (partner_id, kaltura_id),
            'ie_key': KalturaIE.ie_key(),
            'id': video_id,
            'display_id': display_id,
            'title': title,
        }
