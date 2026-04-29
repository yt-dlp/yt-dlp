import re

from .common import InfoExtractor
from ..utils import int_or_none


class RTL2IE(InfoExtractor):
    IE_NAME = 'rtl2'
    _VALID_URL = r'https?://(?:www\.)?rtl2\.de/sendung/[^/]+/(?:video/(?P<vico_id>\d+)[^/]+/(?P<vivi_id>\d+)-|folge/)(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'http://www.rtl2.de/sendung/grip-das-motormagazin/folge/folge-203-0',
        'info_dict': {
            'id': 'folge-203-0',
            'ext': 'f4v',
            'title': 'GRIP sucht den Sommerkönig',
            'description': 'md5:e3adbb940fd3c6e76fa341b8748b562f',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest', 'Failed to download m3u8 information'],
    }, {
        'url': 'http://www.rtl2.de/sendung/koeln-50667/video/5512-anna/21040-anna-erwischt-alex/',
        'info_dict': {
            'id': 'anna-erwischt-alex',
            'ext': 'mp4',
            'title': 'Anna erwischt Alex!',
            'description': 'Anna nimmt ihrem Vater nicht ab, dass er nicht spielt. Und tatsächlich erwischt sie ihn auf frischer Tat.',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest', 'Failed to download m3u8 information'],
    }]

    def _real_extract(self, url):
        vico_id, vivi_id, display_id = self._match_valid_url(url).groups()
        if not vico_id:
            webpage = self._download_webpage(url, display_id)

            mobj = re.search(
                r'data-collection="(?P<vico_id>\d+)"[^>]+data-video="(?P<vivi_id>\d+)"',
                webpage)
            if mobj:
                vico_id = mobj.group('vico_id')
                vivi_id = mobj.group('vivi_id')
            else:
                vico_id = self._html_search_regex(
                    r'vico_id\s*:\s*([0-9]+)', webpage, 'vico_id')
                vivi_id = self._html_search_regex(
                    r'vivi_id\s*:\s*([0-9]+)', webpage, 'vivi_id')

        info = self._download_json(
            'https://service.rtl2.de/api-player-vipo/video.php',
            display_id, query={
                'vico_id': vico_id,
                'vivi_id': vivi_id,
            })
        video_info = info['video']
        title = video_info['titel']

        formats = []

        rtmp_url = video_info.get('streamurl')
        if rtmp_url:
            rtmp_url = rtmp_url.replace('\\', '')
            stream_url = 'mp4:' + self._html_search_regex(r'/ondemand/(.+)', rtmp_url, 'stream URL')
            rtmp_conn = ['S:connect', 'O:1', 'NS:pageUrl:' + url, 'NB:fpad:0', 'NN:videoFunction:1', 'O:0']

            formats.append({
                'format_id': 'rtmp',
                'url': rtmp_url,
                'play_path': stream_url,
                'player_url': 'https://www.rtl2.de/sites/default/modules/rtl2/jwplayer/jwplayer-7.6.0/jwplayer.flash.swf',
                'page_url': url,
                'flash_version': 'LNX 11,2,202,429',
                'rtmp_conn': rtmp_conn,
                'no_resume': True,
                'quality': 1,
            })

        m3u8_url = video_info.get('streamurl_hls')
        if m3u8_url:
            formats.extend(self._extract_akamai_formats(m3u8_url, display_id))

        return {
            'id': display_id,
            'title': title,
            'thumbnail': video_info.get('image'),
            'description': video_info.get('beschreibung'),
            'duration': int_or_none(video_info.get('duration')),
            'formats': formats,
        }
