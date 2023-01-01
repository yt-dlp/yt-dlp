import re

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    HEADRequest,
    int_or_none,
    parse_duration,
    unified_strdate,
)


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
            'upload_date': unified_strdate(self._search_regex(r'datetime="(.+?)"', webpage, 'upload_date', fatal=False))
        }


class LA7PodcastEpisodeIE(InfoExtractor):
    IE_NAME = 'la7.it:pod:episode'
    _VALID_URL = r'https?://(?:www\.)?la7\.it/[^/]+/podcast/([^/]+-)?(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.la7.it/voicetown/podcast/la-carezza-delle-memoria-di-carlo-verdone-23-03-2021-371497',
        'md5': '7737d4d79b3c1a34b3de3e16297119ed',
        'info_dict': {
            'id': '371497',
            'ext': 'mp3',
            'title': '"La carezza delle memoria" di Carlo Verdone',
            'description': 'md5:5abf07c3c551a687db80af3f9ceb7d52',
            'thumbnail': 'https://www.la7.it/sites/default/files/podcast/371497.jpg',
            'upload_date': '20210323',
        },
    }, {
        # embed url
        'url': 'https://www.la7.it/embed/podcast/371497',
        'only_matching': True,
    }, {
        # date already in the title
        'url': 'https://www.la7.it/propagandalive/podcast/lintervista-di-diego-bianchi-ad-annalisa-cuzzocrea-puntata-del-1932021-20-03-2021-371130',
        'only_matching': True,
    }, {
        # title same as show_title
        'url': 'https://www.la7.it/otto-e-mezzo/podcast/otto-e-mezzo-26-03-2021-372340',
        'only_matching': True,
    }]

    def _extract_info(self, webpage, video_id=None, ppn=None):
        if not video_id:
            video_id = self._search_regex(
                r'data-nid=([\'"])(?P<vid>\d+)\1',
                webpage, 'video_id', group='vid')

        media_url = self._search_regex(
            (r'src\s*:\s*([\'"])(?P<url>\S+?mp3.+?)\1',
             r'data-podcast\s*=\s*([\'"])(?P<url>\S+?mp3.+?)\1'),
            webpage, 'media_url', group='url')
        formats = [{
            'url': media_url,
            'format_id': 'http-mp3',
            'ext': 'mp3',
            'acodec': 'mp3',
            'vcodec': 'none',
        }]

        title = self._html_search_regex(
            (r'<div class="title">(?P<title>.+?)</',
             r'<title>(?P<title>[^<]+)</title>',
             r'title:\s*([\'"])(?P<title>.+?)\1'),
            webpage, 'title', group='title')

        description = (
            self._html_search_regex(
                (r'<div class="description">(.+?)</div>',
                 r'<div class="description-mobile">(.+?)</div>',
                 r'<div class="box-txt">([^<]+?)</div>',
                 r'<div class="field-content"><p>(.+?)</p></div>'),
                webpage, 'description', default=None)
            or self._html_search_meta('description', webpage))

        thumb = self._html_search_regex(
            (r'<div class="podcast-image"><img src="(.+?)"></div>',
             r'<div class="container-embed"[^<]+url\((.+?)\);">',
             r'<div class="field-content"><img src="(.+?)"'),
            webpage, 'thumbnail', fatal=False, default=None)

        duration = parse_duration(self._html_search_regex(
            r'<span class="(?:durata|duration)">([\d:]+)</span>',
            webpage, 'duration', fatal=False, default=None))

        date = self._html_search_regex(
            r'class="data">\s*(?:<span>)?([\d\.]+)\s*</',
            webpage, 'date', default=None)

        date_alt = self._search_regex(
            r'(\d+[\./]\d+[\./]\d+)', title, 'date_alt', default=None)
        ppn = ppn or self._search_regex(
            r'ppN:\s*([\'"])(?P<ppn>.+?)\1',
            webpage, 'ppn', group='ppn', default=None)
        # if the date is not in the title
        # and title is the same as the show_title
        # add the date to the title
        if date and not date_alt and ppn and ppn.lower() == title.lower():
            title = f'{title} del {date}'
        return {
            'id': video_id,
            'title': title,
            'description': description,
            'duration': float_or_none(duration),
            'formats': formats,
            'thumbnail': thumb,
            'upload_date': unified_strdate(date),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        return self._extract_info(webpage, video_id)


class LA7PodcastIE(LA7PodcastEpisodeIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'la7.it:podcast'
    _VALID_URL = r'https?://(?:www\.)?la7\.it/(?P<id>[^/]+)/podcast/?(?:$|[#?])'

    _TESTS = [{
        'url': 'https://www.la7.it/propagandalive/podcast',
        'info_dict': {
            'id': 'propagandalive',
            'title': "Propaganda Live",
        },
        'playlist_count_min': 10,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        title = (
            self._html_search_regex(
                r'<h1.*?>(.+?)</h1>', webpage, 'title', fatal=False, default=None)
            or self._og_search_title(webpage))
        ppn = self._search_regex(
            r'window\.ppN\s*=\s*([\'"])(?P<ppn>.+?)\1',
            webpage, 'ppn', group='ppn', default=None)

        entries = []
        for episode in re.finditer(
                r'<div class="container-podcast-property">([\s\S]+?)(?:</div>\s*){3}',
                webpage):
            entries.append(self._extract_info(episode.group(1), ppn=ppn))

        return self.playlist_result(entries, playlist_id, title)
