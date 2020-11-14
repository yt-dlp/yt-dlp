# coding: utf-8
from __future__ import unicode_literals
import re

from .common import InfoExtractor


class ThisVidIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?thisvid\.com/(?P<type>videos|embed)/(?P<id>[A-Za-z0-9-]+/?)'
    _TESTS = [{
        'url': 'https://thisvid.com/videos/french-boy-pantsed/',
        'md5': '3397979512c682f6b85b3b04989df224',
        'info_dict': {
            'id': '2400174',
            'ext': 'mp4',
            'title': 'French Boy Pantsed',
            'thumbnail': 'https://media.thisvid.com/contents/videos_screenshots/2400000/2400174/preview.mp4.jpg',
            'age_limit': 18,
        }
    }, {
        'url': 'https://thisvid.com/embed/2400174/',
        'md5': '3397979512c682f6b85b3b04989df224',
        'info_dict': {
            'id': '2400174',
            'ext': 'mp4',
            'title': 'French Boy Pantsed',
            'thumbnail': 'https://media.thisvid.com/contents/videos_screenshots/2400000/2400174/preview.mp4.jpg',
            'age_limit': 18,
        }
    }]

    def _real_extract(self, url):
        main_id = self._match_id(url)
        webpage = self._download_webpage(url, main_id)

        # URL decryptor was reversed from version 4.0.4, later verified working with 5.2.0 and may change in the future.
        kvs_version = self._html_search_regex(r'<script [^>]+?src="https://thisvid\.com/player/kt_player\.js\?v=(\d+(\.\d+)+)">', webpage, 'kvs_version', fatal=False)
        if not kvs_version.startswith("5."):
            self.report_warning("Major version change (" + kvs_version + ") in player engine--Download may fail.")

        title = self._html_search_regex(r'<title>(?:Video: )?(.+?)(?: - (?:\w+ porn at )?ThisVid(?:.com| tube))?</title>', webpage, 'title')
        # video_id, video_url and license_code from the 'flashvars' JSON object:
        video_id = self._html_search_regex(r"video_id: '([0-9]+)',", webpage, 'video_id')
        video_url = self._html_search_regex(r"video_url: '(function/0/.+?)',", webpage, 'video_url')
        license_code = self._html_search_regex(r"license_code: '([0-9$]{16})',", webpage, 'license_code')
        thumbnail = self._html_search_regex(r"preview_url: '((?:https?:)?//media.thisvid.com/.+?.jpg)',", webpage, 'thumbnail', fatal=False)
        if thumbnail.startswith("//"):
            thumbnail = "https:" + thumbnail
        if (re.match(self._VALID_URL, url).group('type') == "videos"):
            display_id = main_id
        else:
            display_id = self._search_regex(r'<link rel="canonical" href="' + self._VALID_URL + r'">', webpage, 'display_id', fatal=False),

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'url': getrealurl(video_url, license_code),
            'thumbnail': thumbnail,
            'age_limit': 18,
        }


def getrealurl(video_url, license_code):
    urlparts = video_url.split('/')[2:]
    license = getlicensetoken(license_code)
    newmagic = urlparts[5][:32]

    for o in range(len(newmagic) - 1, -1, -1):
        new = ""
        l = (o + sum([int(n) for n in license[o:]])) % 32

        for i in range(0, len(newmagic)):
            if i == o:
                new += newmagic[l]
            elif i == l:
                new += newmagic[o]
            else:
                new += newmagic[i]
        newmagic = new

    urlparts[5] = newmagic + urlparts[5][32:]
    return "/".join(urlparts)


def getlicensetoken(license):
    modlicense = license.replace("$", "").replace("0", "1")
    center = int(len(modlicense) / 2)
    fronthalf = int(modlicense[:center + 1])
    backhalf = int(modlicense[center:])

    modlicense = str(4 * abs(fronthalf - backhalf))
    retval = ""
    for o in range(0, center + 1):
        for i in range(1, 5):
            retval += str((int(license[o + i]) + int(modlicense[o])) % 10)
    return retval
