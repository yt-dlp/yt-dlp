from .common import InfoExtractor

from ..utils import (
    parse_duration,
    js_to_json,
)


class EUScreenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?euscreen\.eu/item.html\?id=(?P<id>[^&?$/]+)'

    _TESTS = [{
        'url': 'https://euscreen.eu/item.html?id=EUS_0EBCBF356BFC4E12A014023BA41BD98C',
        'info_dict': {
            'id': 'EUS_0EBCBF356BFC4E12A014023BA41BD98C',
            'ext': 'mp4',
            'title': "L'effondrement du stade du Heysel",
            'alt_title': 'Collapse of the Heysel Stadium',
            'duration': 318.0,
            'description': 'md5:f0ffffdfce6821139357a1b8359d6152',
            'series': 'JA2 DERNIERE',
            'episode': '-',
            'uploader': 'INA /  France',
            'thumbnail': 'http://images3.noterik.com/domain/euscreenxl/user/eu_ina/video/EUS_0EBCBF356BFC4E12A014023BA41BD98C/image.jpg'
        },
        'params': {'skip_download': True}
    }]

    _payload = b'<fsxml><screen><properties><screenId>-1</screenId></properties><capabilities id="1"><properties><platform>Win32</platform><appcodename>Mozilla</appcodename><appname>Netscape</appname><appversion>5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36</appversion><useragent>Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36</useragent><cookiesenabled>true</cookiesenabled><screenwidth>784</screenwidth><screenheight>758</screenheight><orientation>undefined</orientation><smt_browserid>Sat, 07 Oct 2021 08:56:50 GMT</smt_browserid><smt_sessionid>1633769810758</smt_sessionid></properties></capabilities></screen></fsxml>'

    def _real_extract(self, url):
        id = self._match_id(url)
        args_for_js_request = self._download_webpage(
            'https://euscreen.eu/lou/LouServlet/domain/euscreenxl/html5application/euscreenxlitem',
            id, data=self._payload, query={'actionlist': 'itempage', 'id': id})
        info_js = self._download_webpage(
            'https://euscreen.eu/lou/LouServlet/domain/euscreenxl/html5application/euscreenxlitem',
            id, data=args_for_js_request.replace('screenid', 'screenId').encode())
        video_json = self._parse_json(
            self._search_regex(r'setVideo\(({.+})\)\(\$end\$\)put', info_js, 'Video JSON'),
            id, transform_source=js_to_json)
        meta_json = self._parse_json(
            self._search_regex(r'setData\(({.+})\)\(\$end\$\)', info_js, 'Metadata JSON'),
            id, transform_source=js_to_json)
        formats = [{
            'url': source['src'],
        } for source in video_json.get('sources', [])]

        return {
            'id': id,
            'title': meta_json.get('originalTitle'),
            'alt_title': meta_json.get('title'),
            'duration': parse_duration(meta_json.get('duration')),
            'description': '%s\n%s' % (meta_json.get('summaryOriginal', ''), meta_json.get('summaryEnglish', '')),
            'series': meta_json.get('series') or meta_json.get('seriesEnglish'),
            'episode': meta_json.get('episodeNumber'),
            'uploader': meta_json.get('provider'),
            'thumbnail': meta_json.get('screenshot') or video_json.get('screenshot'),
            'formats': formats,
        }
