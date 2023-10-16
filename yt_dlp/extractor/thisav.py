from .common import InfoExtractor
from ..utils import remove_end


class ThisAVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?thisav\.com/video/(?P<id>[0-9]+)/.*'
    _TESTS = [{
        # jwplayer
        'url': 'http://www.thisav.com/video/47734/%98%26sup1%3B%83%9E%83%82---just-fit.html',
        'md5': '0480f1ef3932d901f0e0e719f188f19b',
        'info_dict': {
            'id': '47734',
            'ext': 'flv',
            'title': '高樹マリア - Just fit',
            'uploader': 'dj7970',
            'uploader_id': 'dj7970'
        }
    }, {
        # html5 media
        'url': 'http://www.thisav.com/video/242352/nerdy-18yo-big-ass-tattoos-and-glasses.html',
        'md5': 'ba90c076bd0f80203679e5b60bf523ee',
        'info_dict': {
            'id': '242352',
            'ext': 'mp4',
            'title': 'Nerdy 18yo Big Ass Tattoos and Glasses',
            'uploader': 'cybersluts',
            'uploader_id': 'cybersluts',
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)

        video_id = mobj.group('id')
        webpage = self._download_webpage(url, video_id)
        title = remove_end(self._html_extract_title(webpage), ' - 視頻 - ThisAV.com-世界第一中文成人娛樂網站')
        video_url = self._html_search_regex(
            r"addVariable\('file','([^']+)'\);", webpage, 'video url', default=None)
        if video_url:
            info_dict = {
                'formats': [{
                    'url': video_url,
                }],
            }
        else:
            entries = self._parse_html5_media_entries(url, webpage, video_id)
            if entries:
                info_dict = entries[0]
            else:
                info_dict = self._extract_jwplayer_data(
                    webpage, video_id, require_title=False)
        uploader = self._html_search_regex(
            r': <a href="http://www\.thisav\.com/user/[0-9]+/(?:[^"]+)">([^<]+)</a>',
            webpage, 'uploader name', fatal=False)
        uploader_id = self._html_search_regex(
            r': <a href="http://www\.thisav\.com/user/[0-9]+/([^"]+)">(?:[^<]+)</a>',
            webpage, 'uploader id', fatal=False)

        info_dict.update({
            'id': video_id,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'title': title,
        })

        return info_dict
