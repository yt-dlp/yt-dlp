import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import int_or_none, unified_strdate


class LA7IE(InfoExtractor):
    IE_NAME = 'la7.it'
    _VALID_URL = r'''(?x)https?://(?:
        (?:www\.)?la7\.it/([^/]+)/(?:rivedila7|video|news)/|
        tg\.la7\.it/repliche-tgla7\?id=
    )(?P<id>.+)'''

    _TESTS = [{
        # single quality video
        'url': 'http://www.la7.it/crozza/video/inccool8-02-10-2015-163722',
        'md5': '8b613ffc0c4bf9b9e377169fc19c214c',
        'info_dict': {
            'id': 'inccool8-02-10-2015-163722',
            'ext': 'mp4',
            'title': 'Inc.Cool8',
            'description': 'Benvenuti nell\'incredibile mondo della INC. COOL. 8. dove “INC.” sta per “Incorporated” “COOL” sta per “fashion” ed Eight sta per il gesto atletico',
            'thumbnail': 're:^https?://.*',
            'upload_date': '20151002',
            'formats': 'count:4',
        },
    }, {
        # multiple quality video
        'url': 'https://www.la7.it/calcio-femminile/news/il-gol-di-lindsey-thomas-fiorentina-vs-milan-serie-a-calcio-femminile-26-11-2022-461736',
        'md5': 'd2370e78f75e8d1238cb3a0db9a2eda3',
        'info_dict': {
            'id': 'il-gol-di-lindsey-thomas-fiorentina-vs-milan-serie-a-calcio-femminile-26-11-2022-461736',
            'ext': 'mp4',
            'title': 'Il gol di Lindsey Thomas | Fiorentina vs Milan | Serie A Calcio Femminile',
            'description': 'Il gol di Lindsey Thomas | Fiorentina vs Milan | Serie A Calcio Femminile',
            'thumbnail': 're:^https?://.*',
            'upload_date': '20221126',
            'formats': 'count:8',
        },
    }, {
        'url': 'http://www.la7.it/omnibus/rivedila7/omnibus-news-02-07-2016-189077',
        'only_matching': True,
    }]
    _HOST = 'https://awsvodpkg.iltrovatore.it'

    def _generate_mp4_url(self, quality, m3u8_formats):
        for f in m3u8_formats:
            if f['vcodec'] != 'none' and quality in f['url']:
                http_url = f'{self._HOST}{quality}.mp4'

                urlh = self._request_webpage(
                    HEADRequest(http_url), quality,
                    note='Check filesize', fatal=False)
                if urlh:
                    http_f = f.copy()
                    del http_f['manifest_url']
                    http_f.update({
                        'format_id': http_f['format_id'].replace('hls-', 'https-'),
                        'url': http_url,
                        'protocol': 'https',
                        'filesize_approx': int_or_none(urlh.headers.get('Content-Length', None)),
                    })
                    return http_f
                return None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if re.search(r'(?i)(drmsupport\s*:\s*true)\s*', webpage):
            self.report_drm(video_id)

        video_path = self._search_regex(
            r'(/content/[\w/,]+?)\.mp4(?:\.csmil)?/master\.m3u8', webpage, 'video_path')

        formats = self._extract_mpd_formats(
            f'{self._HOST}/local/dash/,{video_path}.mp4.urlset/manifest.mpd',
            video_id, mpd_id='dash', fatal=False)
        m3u8_formats = self._extract_m3u8_formats(
            f'{self._HOST}/local/hls/,{video_path}.mp4.urlset/master.m3u8',
            video_id, 'mp4', m3u8_id='hls', fatal=False)
        formats.extend(m3u8_formats)

        for q in filter(None, video_path.split(',')):
            http_f = self._generate_mp4_url(q, m3u8_formats)
            if http_f:
                formats.append(http_f)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': formats,
            'upload_date': unified_strdate(self._search_regex(r'datetime="(.+?)"', webpage, 'upload_date', fatal=False)),
        }
