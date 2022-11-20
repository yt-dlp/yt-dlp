from .common import InfoExtractor
from urllib.parse import urlparse
from re import sub
from datetime import datetime


class RadioRadicaleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radioradicale\.it/scheda/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.radioradicale.it/scheda/471591',
        'info_dict': {
            'id': '471591',
            'ext': 'mp4',
            'title': 'Conversazione di Giuseppe Di Leo con Paolo Isotta, musicologo e scrittore italiano, sull\'opera e la figura di Piero Buscaroli',
            'upload_date': '20160407',
            'creator': 'Giuseppe Di Leo',
            'timestamp': 1460044800.0,
            'location': 'Napoli',
        }
    }]

    def _real_extract(self, url):
        months = {
            'GEN': 1,
            'FEB': 2,
            'MAR': 3,
            'APR': 4,
            'MAG': 5,
            'GIU': 6,
            'LUG': 7,
            'AGO': 8,
            'SET': 9,
            'OTT': 10,
            'NOV': 11,
            'DIC': 12
        }

        regex_strs = [
            r'<h1[^>]+class=(["\'])titolo-scheda\1[^>]*>(?P<title>[^<]+)',
            r' \| di&nbsp;(?P<creator>.+?) - (?P<location>.+?) - (?P<hour>\d+):(?P<minute>\d+)',
            r'<div[^>]+class=(["\'])data\1[^>]*>[ \n]*<span[^>]+class=(["\'])data_day\2[^>]*>(?P<day>\d+)<\/span>[ \n]*<span[^>]+class=(["\'])data_month\4[^>]*>(?P<month>\w+)<\/span>[ \n]*<span[^>]+class=(["\'])data_year\6[^>]*>(?P<year>\d+)<\/span>[ \n]*<\/div>'
        ]

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        m3u8_base = urlparse(self._search_regex(
            r'href="(rtsp://video.radioradicale.it:80/.+?)"', webpage, 'video ref'))
        m3u8_base = m3u8_base._replace(scheme='https', netloc=m3u8_base.hostname)

        playlist = self._extract_m3u8_formats_and_subtitles(
            m3u8_base._replace(path=m3u8_base.path + '/playlist.m3u8').geturl(), video_id)

        playlist[0][0]['fragment_base_url'] = m3u8_base.geturl()
        chunks = sub('#.*', '', self._download_webpage(
                     playlist[0][0]['url'], video_id, note='Downloading chunk list')).strip().split()
        playlist[0][0]['fragments'] = [{'path': chunk} for chunk in chunks]

        return {
            'id': video_id,
            'formats': playlist[0],
            'title': self._html_search_regex(regex_strs[0], webpage, 'title', group='title'),
            'creator': self._search_regex(regex_strs[1], webpage, 'creator', group='creator'),
            'location': self._search_regex(regex_strs[1], webpage, 'location', group='location'),
            'timestamp': datetime(
                int(self._html_search_regex(regex_strs[2], webpage, 'release year', group='year')),
                months[self._html_search_regex(regex_strs[2], webpage, 'release month', group='month')],
                int(self._html_search_regex(regex_strs[2], webpage, 'release day', group='day')),
                int(self._search_regex(regex_strs[1], webpage, 'release hour', group='hour')),
                int(self._search_regex(regex_strs[1], webpage, 'release minute', group='minute'))
            ).timestamp(),
        }
