import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    decode_packed_codes,
    urlencode_postdata,
)


class SCTEBaseIE(InfoExtractor):
    _LOGIN_URL = 'https://www.scte.org/SCTE/Sign_In.aspx'
    _NETRC_MACHINE = 'scte'

    def _perform_login(self, username, password):
        login_popup = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login popup')

        def is_logged(webpage):
            return any(re.search(p, webpage) for p in (
                r'class=["\']welcome\b', r'>Sign Out<'))

        # already logged in
        if is_logged(login_popup):
            return

        login_form = self._hidden_inputs(login_popup)

        login_form.update({
            'ctl01$TemplateBody$WebPartManager1$gwpciNewContactSignInCommon$ciNewContactSignInCommon$signInUserName': username,
            'ctl01$TemplateBody$WebPartManager1$gwpciNewContactSignInCommon$ciNewContactSignInCommon$signInPassword': password,
            'ctl01$TemplateBody$WebPartManager1$gwpciNewContactSignInCommon$ciNewContactSignInCommon$RememberMe': 'on',
        })

        response = self._download_webpage(
            self._LOGIN_URL, None, 'Logging in',
            data=urlencode_postdata(login_form))

        if '|pageRedirect|' not in response and not is_logged(response):
            error = self._html_search_regex(
                r'(?s)<[^>]+class=["\']AsiError["\'][^>]*>(.+?)</',
                response, 'error message', default=None)
            if error:
                raise ExtractorError(f'Unable to login: {error}', expected=True)
            raise ExtractorError('Unable to log in')


class SCTEIE(SCTEBaseIE):
    _WORKING = False
    _VALID_URL = r'https?://learning\.scte\.org/mod/scorm/view\.php?.*?\bid=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://learning.scte.org/mod/scorm/view.php?id=31484',
        'info_dict': {
            'title': 'Introduction to DOCSIS Engineering Professional',
            'id': '31484',
        },
        'playlist_count': 5,
        'skip': 'Requires account credentials',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        title = self._search_regex(r'<h1>(.+?)</h1>', webpage, 'title')

        context_id = self._search_regex(r'context-(\d+)', webpage, video_id)
        content_base = f'https://learning.scte.org/pluginfile.php/{context_id}/mod_scorm/content/8/'
        context = decode_packed_codes(self._download_webpage(
            f'{content_base}mobile/data.js', video_id))

        data = self._parse_xml(
            self._search_regex(
                r'CreateData\(\s*"(.+?)"', context, 'data').replace(r"\'", "'"),
            video_id)

        entries = []
        for asset in data.findall('.//asset'):
            asset_url = asset.get('url')
            if not asset_url or not asset_url.endswith('.mp4'):
                continue
            asset_id = self._search_regex(
                r'video_([^_]+)_', asset_url, 'asset id', default=None)
            if not asset_id:
                continue
            entries.append({
                'id': asset_id,
                'title': title,
                'url': content_base + asset_url,
            })

        return self.playlist_result(entries, video_id, title)


class SCTECourseIE(SCTEBaseIE):
    _WORKING = False
    _VALID_URL = r'https?://learning\.scte\.org/(?:mod/sub)?course/view\.php?.*?\bid=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://learning.scte.org/mod/subcourse/view.php?id=31491',
        'only_matching': True,
    }, {
        'url': 'https://learning.scte.org/course/view.php?id=3639',
        'only_matching': True,
    }, {
        'url': 'https://learning.scte.org/course/view.php?id=3073',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        course_id = self._match_id(url)

        webpage = self._download_webpage(url, course_id)

        title = self._search_regex(
            r'<h1>(.+?)</h1>', webpage, 'title', default=None)

        entries = []
        for mobj in re.finditer(
                r'''(?x)
                    <a[^>]+
                        href=(["\'])
                        (?P<url>
                            https?://learning\.scte\.org/mod/
                            (?P<kind>scorm|subcourse)/view\.php?(?:(?!\1).)*?
                            \bid=\d+
                        )
                    ''',
                webpage):
            item_url = mobj.group('url')
            if item_url == url:
                continue
            ie = (SCTEIE.ie_key() if mobj.group('kind') == 'scorm'
                  else SCTECourseIE.ie_key())
            entries.append(self.url_result(item_url, ie=ie))

        return self.playlist_result(entries, course_id, title)
