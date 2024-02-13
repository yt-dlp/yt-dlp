import re

from .common import InfoExtractor


class ToypicsIE(InfoExtractor):
    _WORKING = False
    IE_DESC = 'Toypics video'
    _VALID_URL = r'https?://videos\.toypics\.net/view/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://videos.toypics.net/view/514/chancebulged,-2-1/',
        'md5': '16e806ad6d6f58079d210fe30985e08b',
        'info_dict': {
            'id': '514',
            'ext': 'mp4',
            'title': "Chance-Bulge'd, 2",
            'age_limit': 18,
            'uploader': 'kidsune',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        formats = self._parse_html5_media_entries(
            url, webpage, video_id)[0]['formats']
        title = self._html_search_regex([
            r'<h1[^>]+class=["\']view-video-title[^>]+>([^<]+)</h',
            r'<title>([^<]+) - Toypics</title>',
        ], webpage, 'title')

        uploader = self._html_search_regex(
            r'More videos from <strong>([^<]+)</strong>', webpage, 'uploader',
            fatal=False)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'uploader': uploader,
            'age_limit': 18,
        }


class ToypicsUserIE(InfoExtractor):
    _WORKING = False
    IE_DESC = 'Toypics user profile'
    _VALID_URL = r'https?://videos\.toypics\.net/(?!view)(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'http://videos.toypics.net/Mikey',
        'info_dict': {
            'id': 'Mikey',
        },
        'playlist_mincount': 19,
    }

    def _real_extract(self, url):
        username = self._match_id(url)

        profile_page = self._download_webpage(
            url, username, note='Retrieving profile page')

        video_count = int(self._search_regex(
            r'public/">Public Videos \(([0-9]+)\)</a></li>', profile_page,
            'video count'))

        PAGE_SIZE = 8
        urls = []
        page_count = (video_count + PAGE_SIZE + 1) // PAGE_SIZE
        for n in range(1, page_count + 1):
            lpage_url = url + '/public/%d' % n
            lpage = self._download_webpage(
                lpage_url, username,
                note='Downloading page %d/%d' % (n, page_count))
            urls.extend(
                re.findall(
                    r'<div[^>]+class=["\']preview[^>]+>\s*<a[^>]+href="(https?://videos\.toypics\.net/view/[^"]+)"',
                    lpage))

        return {
            '_type': 'playlist',
            'id': username,
            'entries': [{
                '_type': 'url',
                'url': eurl,
                'ie_key': 'Toypics',
            } for eurl in urls]
        }
