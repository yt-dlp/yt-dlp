from locale import LC_ALL, setlocale
from .common import InfoExtractor
from urllib.parse import urlparse
from re import sub
from datetime import datetime
from os.path import dirname


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
        setlocale(LC_ALL, '')

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_info = self._parse_json(self._search_regex(
            r'jQuery\.extend\(Drupal\.settings\s*,\s*({.+?})\);',
            webpage, 'drupal settings'), video_id)['RRscheda']

        playlist = self._extract_m3u8_formats_and_subtitles(
            video_info['playlist'][0]['sources'][0]['src'], video_id)

        base_url = urlparse(video_info['playlist'][0]['sources'][0]['src'])._replace(
            params='', query='', fragment='')

        playlist[0][0]['fragment_base_url'] = \
            base_url._replace(path=dirname(base_url.path)).geturl()
        chunks = sub('#.*', '', self._download_webpage(
                     playlist[0][0]['url'], video_id, note='Downloading chunk list')).strip().split()
        playlist[0][0]['fragments'] = [{'path': chunk} for chunk in chunks]

        name_time = r' \| di&nbsp;(?P<creator>.+?) - (?P<location>.+?) - (?P<hour>\d+):(?P<minute>\d+)'

        return {
            'id': video_id,
            'formats': playlist[0],
            'title': video_info['playlist'][0]['title'],
            'creator': self._search_regex(name_time, webpage, 'creator', group='creator'),
            'location': video_info['luogo'],
            'timestamp': datetime.strptime(video_info['data'], '%d %B %Y').replace(
                hour=int(self._search_regex(name_time, webpage, 'release hour', group='hour')),
                minute=int(self._search_regex(name_time, webpage, 'release minute', group='minute'))
            ).timestamp(),
        }
