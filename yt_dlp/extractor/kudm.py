import urllib

from .common import InfoExtractor
from .openload import PhantomJSwrapper
from ..utils import unescapeHTML, parse_qs

# http://www.kudm.net/ has two sites:
# * https://www.sbdm.net/
# * https://www.gqdm.net/


class SbdmIE(InfoExtractor):
    _VALID_URL = r'(?x)(?P<season>https?://www\.sbdm\.net/[^/]+/\d+)/v.html\?(?P<id>\d+-\d+-\d+)'

    _TESTS = [{
        'url': 'https://www.sbdm.net/LADM/7025/v.html?7025-0-11',
        'info_dict': {
            'id': '7025-0-11',
            'ext': 'mp4',
            'season': '迷途貓 OVERRUN',
            'title': '迷途貓 OVERRUN 第12集BD版',
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        season_url = mobj.group('season')

        season_url_parsed = urllib.parse.urlparse(season_url)
        season_url_path = url[len(season_url_parsed.scheme + '://' + season_url_parsed.netloc):]

        phantom = PhantomJSwrapper(self)

        season_page, _ = phantom.get(season_url, video_id=video_id, note='Downloading season page')
        season_title = self._search_regex(r'<h1>(?P<season_title>[^<]+)</h1>', season_page, 'title')

        title_pattern = r'title="(?P<title>[^"]+)"\s+href="' + season_url_path.replace('?', r'\?')
        title = self._search_regex(title_pattern, season_page, 'title')

        video_page, _ = phantom.get(url, video_id=video_id, note='Downloading video page')
        iframe_url = unescapeHTML(self._search_regex(r'<iframe[^<]+?src="(?P<url>[^"]+)"', video_page, 'iframe url'))
        m3u8_url = parse_qs(iframe_url)['a'][0]

        return {
            'id': video_id,
            'season': season_title,
            'title': f'{season_title} {title}',
            'formats': [{
                'url': m3u8_url,
                'protocol': 'm3u8_fake_header',
                'ext': 'mp4',
            }]
        }


class GqdmIE(InfoExtractor):
    _VALID_URL = r'(?x)https?://www\.gqdm\.net/index.php/vod/play/id/(?P<series_id>\d+)/sid/(?P<sid>\d+)/nid/(?P<nid>\d+).html'

    _TESTS = [{
        'url': 'https://www.gqdm.net/index.php/vod/play/id/538/sid/1/nid/3.html',
        'info_dict': {
            'id': '538_1_3',
            'ext': 'mp4',
            'season': '碧蓝航线',
            'title': '碧蓝航线 第3集BD无修',
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        series_id, sid, nid = mobj.group('series_id'), mobj.group('sid'), mobj.group('nid')
        video_id = f'{series_id}_{sid}_{nid}'

        webpage = self._download_webpage(url, video_id)
        season_title = self._search_regex(r'<h2 class="title[^>]+>(?P<season_title>[^<]+)</h2>', webpage, 'season_title')

        url_parsed = urllib.parse.urlparse(url)
        title = self._search_regex(f'<a href="{url_parsed.path}">(?P<title>[^<]+)</a>', webpage, 'title')

        play_info = self._search_json(r'player_aaaa\s*=', webpage, 'play_info', video_id, default={})

        return {
            'id': video_id,
            'season': season_title,
            'title': f'{season_title} {title}',
            'formats': [{
                'url': play_info['url'],
                'protocol': 'm3u8_fake_header',
                'ext': 'mp4',
            }]
        }
