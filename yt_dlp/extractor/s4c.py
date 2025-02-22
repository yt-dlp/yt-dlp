from .common import InfoExtractor
from ..utils import traverse_obj, url_or_none


class S4CIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?s4c\.cymru/clic/programme/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.s4c.cymru/clic/programme/861362209',
        'info_dict': {
            'id': '861362209',
            'ext': 'mp4',
            'title': 'Y Swn',
            'description': 'md5:f7681a30e4955b250b3224aa9fe70cf0',
            'duration': 5340,
            'thumbnail': 'https://www.s4c.cymru/amg/1920x1080/Y_Swn_2023S4C_099_ii.jpg',
        },
    }, {
        'url': 'https://www.s4c.cymru/clic/programme/856636948',
        'info_dict': {
            'id': '856636948',
            'ext': 'mp4',
            'title': 'Am Dro',
            'duration': 2880,
            'description': 'md5:100d8686fc9a632a0cb2db52a3433ffe',
            'thumbnail': 'https://www.s4c.cymru/amg/1920x1080/Am_Dro_2022-23S4C_P6_4005.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        details = self._download_json(
            f'https://www.s4c.cymru/df/full_prog_details?lang=e&programme_id={video_id}',
            video_id, fatal=False)

        player_config = self._download_json(
            'https://player-api.s4c-cdn.co.uk/player-configuration/prod', video_id, query={
                'programme_id': video_id,
                'signed': '0',
                'lang': 'en',
                'mode': 'od',
                'appId': 'clic',
                'streamName': '',
            }, note='Downloading player config JSON')
        subtitles = {}
        for sub in traverse_obj(player_config, ('subtitles', lambda _, v: url_or_none(v['0']))):
            subtitles.setdefault(sub.get('3', 'en'), []).append({
                'url': sub['0'],
                'name': sub.get('1'),
            })
        m3u8_url = self._download_json(
            'https://player-api.s4c-cdn.co.uk/streaming-urls/prod', video_id, query={
                'mode': 'od',
                'application': 'clic',
                'region': 'WW',
                'extra': 'false',
                'thirdParty': 'false',
                'filename': player_config['filename'],
            }, note='Downloading streaming urls JSON')['hls']

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls'),
            'subtitles': subtitles,
            'thumbnail': url_or_none(player_config.get('poster')),
            **traverse_obj(details, ('full_prog_details', 0, {
                'title': (('programme_title', 'series_title'), {str}),
                'description': ('full_billing', {str.strip}),
                'duration': ('duration', {lambda x: int(x) * 60}),
            }), get_all=False),
        }


class S4CSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?s4c\.cymru/clic/series/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.s4c.cymru/clic/series/864982911',
        'playlist_mincount': 6,
        'info_dict': {
            'id': '864982911',
            'title': 'Iaith ar Daith',
        },
    }, {
        'url': 'https://www.s4c.cymru/clic/series/866852587',
        'playlist_mincount': 8,
        'info_dict': {
            'id': '866852587',
            'title': 'FFIT Cymru',
        },
    }]

    def _real_extract(self, url):
        series_id = self._match_id(url)
        series_details = self._download_json(
            'https://www.s4c.cymru/df/series_details', series_id, query={
                'lang': 'e',
                'series_id': series_id,
                'show_prog_in_series': 'Y',
            }, note='Downloading series details JSON')

        return self.playlist_result(
            [self.url_result(f'https://www.s4c.cymru/clic/programme/{episode_id}', S4CIE, episode_id)
             for episode_id in traverse_obj(series_details, ('other_progs_in_series', ..., 'id'))],
            series_id, traverse_obj(series_details, ('full_prog_details', 0, 'series_title', {str})))
