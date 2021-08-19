# coding: utf-8
from __future__ import unicode_literals

import hashlib
import re

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_request,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    sanitized_Request,
    urlencode_postdata,
)


class FC2IE(InfoExtractor):
    _VALID_URL = r'^(?:https?://video\.fc2\.com/(?:[^/]+/)*content/|fc2:)(?P<id>[^/]+)'
    IE_NAME = 'fc2'
    _NETRC_MACHINE = 'fc2'
    _TESTS = [{
        'url': 'http://video.fc2.com/en/content/20121103kUan1KHs',
        'md5': 'a6ebe8ebe0396518689d963774a54eb7',
        'info_dict': {
            'id': '20121103kUan1KHs',
            'ext': 'flv',
            'title': 'Boxing again with Puff',
        },
    }, {
        'url': 'http://video.fc2.com/en/content/20150125cEva0hDn/',
        'info_dict': {
            'id': '20150125cEva0hDn',
            'ext': 'mp4',
        },
        'params': {
            'username': 'ytdl@yt-dl.org',
            'password': '(snip)',
        },
        'skip': 'requires actual password',
    }, {
        'url': 'http://video.fc2.com/en/a/content/20130926eZpARwsF',
        'only_matching': True,
    }]

    def _login(self):
        username, password = self._get_login_info()
        if username is None or password is None:
            return False

        # Log in
        login_form_strs = {
            'email': username,
            'password': password,
            'done': 'video',
            'Submit': ' Login ',
        }

        login_data = urlencode_postdata(login_form_strs)
        request = sanitized_Request(
            'https://secure.id.fc2.com/index.php?mode=login&switch_language=en', login_data)

        login_results = self._download_webpage(request, None, note='Logging in', errnote='Unable to log in')
        if 'mode=redirect&login=done' not in login_results:
            self.report_warning('unable to log in: bad username or password')
            return False

        # this is also needed
        login_redir = sanitized_Request('http://id.fc2.com/?mode=redirect&login=done')
        self._download_webpage(
            login_redir, None, note='Login redirect', errnote='Login redirect failed')

        return True

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._login()
        webpage = None
        if not url.startswith('fc2:'):
            webpage = self._download_webpage(url, video_id)
            self._downloader.cookiejar.clear_session_cookies()  # must clear
            self._login()

        title = 'FC2 video %s' % video_id
        thumbnail = None
        if webpage is not None:
            title = self._og_search_title(webpage)
            thumbnail = self._og_search_thumbnail(webpage)
        refer = url.replace('/content/', '/a/content/') if '/a/content/' not in url else url

        mimi = hashlib.md5((video_id + '_gGddgPfeaf_gzyr').encode('utf-8')).hexdigest()

        info_url = (
            'http://video.fc2.com/ginfo.php?mimi={1:s}&href={2:s}&v={0:s}&fversion=WIN%2011%2C6%2C602%2C180&from=2&otag=0&upid={0:s}&tk=null&'.
            format(video_id, mimi, compat_urllib_request.quote(refer, safe=b'').replace('.', '%2E')))

        info_webpage = self._download_webpage(
            info_url, video_id, note='Downloading info page')
        info = compat_urlparse.parse_qs(info_webpage)

        if 'err_code' in info:
            # most of the time we can still download wideo even if err_code is 403 or 602
            self.report_warning(
                'Error code was: %s... but still trying' % info['err_code'][0])

        if 'filepath' not in info:
            raise ExtractorError('Cannot download file. Are you logged in?')

        video_url = info['filepath'][0] + '?mid=' + info['mid'][0]
        title_info = info.get('title')
        if title_info:
            title = title_info[0]

        return {
            'id': video_id,
            'title': title,
            'url': video_url,
            'ext': 'flv',
            'thumbnail': thumbnail,
        }


class FC2EmbedIE(InfoExtractor):
    _VALID_URL = r'https?://video\.fc2\.com/flv2\.swf\?(?P<query>.+)'
    IE_NAME = 'fc2:embed'

    _TEST = {
        'url': 'http://video.fc2.com/flv2.swf?t=201404182936758512407645&i=20130316kwishtfitaknmcgd76kjd864hso93htfjcnaogz629mcgfs6rbfk0hsycma7shkf85937cbchfygd74&i=201403223kCqB3Ez&d=2625&sj=11&lang=ja&rel=1&from=11&cmt=1&tk=TlRBM09EQTNNekU9&tl=プリズン･ブレイク%20S1-01%20マイケル%20【吹替】',
        'md5': 'b8aae5334cb691bdb1193a88a6ab5d5a',
        'info_dict': {
            'id': '201403223kCqB3Ez',
            'ext': 'flv',
            'title': 'プリズン･ブレイク S1-01 マイケル 【吹替】',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        query = compat_parse_qs(mobj.group('query'))

        video_id = query['i'][-1]
        title = query.get('tl', ['FC2 video %s' % video_id])[0]

        sj = query.get('sj', [None])[0]
        thumbnail = None
        if sj:
            # See thumbnailImagePath() in ServerConst.as of flv2.swf
            thumbnail = 'http://video%s-thumbnail.fc2.com/up/pic/%s.jpg' % (
                sj, '/'.join((video_id[:6], video_id[6:8], video_id[-2], video_id[-1], video_id)))

        return {
            '_type': 'url_transparent',
            'ie_key': FC2IE.ie_key(),
            'url': 'fc2:%s' % video_id,
            'title': title,
            'thumbnail': thumbnail,
        }
