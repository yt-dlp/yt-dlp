import re

from .common import InfoExtractor
from ..networking import Request
from ..utils import base_url, parse_qs, remove_start, urlencode_postdata
from ..utils.traversal import traverse_obj


class GDCVaultIE(InfoExtractor):
    _WORKING = True
    _VALID_URL = r'https?://(?:www\.)?gdcvault\.com/play/(?P<id>\d+)(?:/(?P<name>[\w-]+))?'
    _NETRC_MACHINE = 'gdcvault'
    _TESTS = [
        {
            'url': 'https://www.gdcvault.com/play/1019721/Doki-Doki-Universe-Sweet-Simple',
            'md5': '6f79bb5f7a743e6d7464877835405964',
            'info_dict': {
                'id': '1019721',
                'display_id': 'Doki-Doki-Universe-Sweet-Simple',
                'ext': 'mp4',
                'title': 'Doki-Doki Universe: Sweet, Simple and Genuine (GDC Next 10)',
            },
        },
        {
            'url': 'https://www.gdcvault.com/play/1015683/Embracing-the-Dark-Art-of',
            'info_dict': {
                'id': '1015683',
                'display_id': 'Embracing-the-Dark-Art-of',
                'ext': 'mp4',
                'title': 'Embracing the Dark Art of Mathematical Modeling in AI',
            },
        },
        {
            # missing login to assert correct MD5 for test case
            'url': 'https://gdcvault.com/play/1035154/How-Tabletop-Design-Helped-Shape',
            'md5': '',
            'info_dict': {
                'id': '1035154',
                'display_id': 'How-Tabletop-Design-Helped-Shape',
                'ext': 'mp4',
                'title': "How Tabletop Design Helped Shape 'UFO 50'",
            },
            'skip': 'Requires login',
        },
        {
            'url': 'http://gdcvault.com/play/1020791/',
            'only_matching': True,
        },
        {
            # Historically was a hard-coded hostname
            'url': 'https://gdcvault.com/play/1023460/Tenacious-Design-and-The-Interface',
            'md5': '250f70ff9dfefbcc644c0a2d62767ce7',
            'info_dict': {
                'id': '1023460',
                'ext': 'mp4',
                'display_id': 'Tenacious-Design-and-The-Interface',
                'title': 'Tenacious Design and The Interface of \'Destiny\'',
            },
        },
        {
            # Includes Ja/En Subtitles. Historically had multiple audio streams. Currently only
            # has Japanese.
            'url': 'https://www.gdcvault.com/play/1014631/Classic-Game-Postmortem-PAC',
            'info_dict': {
                'id': '1014631',
                'ext': 'mp4',
                'display_id': 'Classic-Game-Postmortem-PAC',
                'title': 'Classic Game Postmortem - PAC-MAN',
            },
            'params': {
                'skip_download': True,  # Requires rtmpdump
            },
        },
        {
            # legacy native HTML video player
            'url': 'https://www.gdcvault.com/play/1435/An-American-engine-in-Tokyo',
            'info_dict': {
                'id': '1435',
                'display_id': 'An-American-engine-in-Tokyo',
                'ext': 'mp4',
                'title': 'An American engine in Tokyo: The collaboration of Epic Games and Square Enix for THE LAST REMNANT',
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

        request = Request(login_url, urlencode_postdata(login_form))
        request.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        self._download_webpage(request, display_id, 'Logging in')
        start_page = self._download_webpage(webpage_url, display_id, 'Getting authenticated video page')
        self._download_webpage(logout_url, display_id, 'Logging out')

        return start_page

    def _real_extract(self, url):
        video_id, name = self._match_valid_url(url).groups()
        display_id = name or video_id

        webpage_url = 'http://www.gdcvault.com/play/' + video_id
        start_page = self._download_webpage(webpage_url, display_id)
        title = remove_start(self._html_extract_title(start_page), 'GDC Vault - ')
        rich_title = self._html_search_regex(
            r'<[td]{2}[^>]*>\s*<strong>Session Name:?</strong>\s*</[td]{2}>\s*<[td]{2}[^>]*>\s*(.*?)\s*</[td]{2}>',
            start_page, 'title', fatal=False)
        if rich_title:
            title = rich_title

        # query the iframe for the real video
        iframe_url = self._search_regex(
            r'<iframe[^/]+src="(https://gdcvault.blazestreaming.com/\?id=[a-z0-9]+)"',
            start_page, 'iframe_url', default=None, fatal=False)

        if iframe_url:
            # request the iframe webpage to get the "real" video url, walking to the
            # javascript file defining the source URL
            blaze_id = traverse_obj(parse_qs(iframe_url), ('id', -1))
            player_baseurl = base_url(iframe_url)

            # Unclear if this is required, as the javascript file appears to
            # respond to some requests headers with dynamic content for the
            # same requested URL later on.
            _player_page = self._download_webpage(iframe_url, display_id)

            js_url = f'{player_baseurl}script_VOD.js'
            player_url_js = self._download_webpage(js_url, display_id)

            cdn_url_js = self._search_regex(
                r'PLAYBACK_URL[\s]*=[\s]*\'(https://[^\']+\'\+videoId\+\'[a-z0-9/]+/index.m3u8)',
                player_url_js, 'cdn_url_js')
            cdn_url_real = cdn_url_js.replace("'+videoId+'", blaze_id)

            m3u8_formats, m3u8_subs = self._extract_m3u8_formats_and_subtitles(cdn_url_real, video_id)

            title = self._html_search_regex(
                r'<[td]{2}[^>]*>\s*<strong>Session Name:?</strong>\s*</[td]{2}>\s*<[td]{2}[^>]*>\s*(.*?)\s*</[td]{2}>',
                start_page, 'title', fatal=False)
            if not title:
                title = remove_start(self._html_extract_title(start_page), 'GDC Vault - ')

            if m3u8_formats and title:
                return {
                    'id': video_id,
                    'display_id': display_id,
                    'title': title,
                    'formats': m3u8_formats,
                    'subtitles': m3u8_subs,
                }

        # fallback to searching for a raw MP4 file for older webpages.
        self.to_screen('falling back to native HTML video')
        media_entries = self._parse_html5_media_entries(url, start_page, video_id)
        assert (len(self._parse_html5_media_entries(url, start_page, video_id)) == 1)

        info = media_entries[0]
        info.update({
            'title': title,
            'id': video_id,
            'display_id': display_id,
        })
        return info
