from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils import (
    HEADRequest,
    remove_start,
    sanitized_Request,
    smuggle_url,
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
        {
            # Kaltura embed, whitespace between quote and embedded URL in iframe's src
            'url': 'https://www.gdcvault.com/play/1025699',
            'info_dict': {
                'id': '0_zagynv0a',
                'ext': 'mp4',
                'title': 'Tech Toolbox',
                'upload_date': '20190408',
                'uploader_id': 'joe@blazestreaming.com',
                'timestamp': 1554764629,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # HTML5 video
            'url': 'http://www.gdcvault.com/play/1014846/Conference-Keynote-Shigeru',
            'only_matching': True,
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
        start_page = self._download_webpage(webpage_url, display_id, 'Getting authenticated video page')
        self._download_webpage(logout_url, display_id, 'Logging out')

        return start_page

    def _real_extract(self, url):
        video_id, name = re.match(self._VALID_URL, url).groups()
        display_id = name or video_id

        webpage_url = 'http://www.gdcvault.com/play/' + video_id
        start_page = self._download_webpage(webpage_url, display_id)

        direct_url = self._search_regex(
            r's1\.addVariable\("file",\s*encodeURIComponent\("(/[^"]+)"\)\);',
            start_page, 'url', default=None)
        if direct_url:
            title = self._html_search_regex(
                r'<td><strong>Session Name:?</strong></td>\s*<td>(.*?)</td>',
                start_page, 'title')
            video_url = 'http://www.gdcvault.com' + direct_url
            # resolve the url so that we can detect the correct extension
            video_url = self._request_webpage(
                HEADRequest(video_url), video_id).geturl()

            return {
                'id': video_id,
                'display_id': display_id,
                'url': video_url,
                'title': title,
            }

        embed_url = KalturaIE._extract_url(start_page)
        if embed_url:
            embed_url = smuggle_url(embed_url, {'source_url': url})
            ie_key = 'Kaltura'
        else:
            PLAYER_REGEX = r'<iframe src="(?P<xml_root>.+?)/(?:gdc-)?player.*?\.html.*?".*?</iframe>'

            xml_root = self._html_search_regex(
                PLAYER_REGEX, start_page, 'xml root', default=None)
            if xml_root is None:
                # Probably need to authenticate
                login_res = self._login(webpage_url, display_id)
                if login_res is None:
                    self.report_warning('Could not login.')
                else:
                    start_page = login_res
                    # Grab the url from the authenticated page
                    xml_root = self._html_search_regex(
                        PLAYER_REGEX, start_page, 'xml root')

            xml_name = self._html_search_regex(
                r'<iframe src=".*?\?xml(?:=|URL=xml/)(.+?\.xml).*?".*?</iframe>',
                start_page, 'xml filename', default=None)
            if not xml_name:
                info = self._parse_html5_media_entries(url, start_page, video_id)[0]
                info.update({
                    'title': remove_start(self._search_regex(
                        r'>Session Name:\s*<.*?>\s*<td>(.+?)</td>', start_page,
                        'title', default=None) or self._og_search_title(
                        start_page, default=None), 'GDC Vault - '),
                    'id': video_id,
                    'display_id': display_id,
                })
                return info
            embed_url = '%s/xml/%s' % (xml_root, xml_name)
            ie_key = 'DigitallySpeaking'

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'display_id': display_id,
            'url': embed_url,
            'ie_key': ie_key,
        }
