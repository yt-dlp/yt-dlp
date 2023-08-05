from .common import InfoExtractor
from ..utils import traverse_obj


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
            'thumbnail': 'https://www.s4c.cymru/amg/1920x1080/Y_Swn_2023S4C_099_ii.jpg'
        },
    }, {
        'url': 'https://www.s4c.cymru/clic/programme/856636948',
        'info_dict': {
            'id': '856636948',
            'ext': 'mp4',
            'title': 'Am Dro',
            'duration': 2880,
            'description': 'md5:100d8686fc9a632a0cb2db52a3433ffe',
            'thumbnail': 'https://www.s4c.cymru/amg/1920x1080/Am_Dro_2022-23S4C_P6_4005.jpg'
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        details = self._download_json(
            f'https://www.s4c.cymru/df/full_prog_details?lang=e&programme_id={video_id}',
            video_id, fatal=False)

        playerConfig = self._download_json(
            'https://player-api.s4c-cdn.co.uk/player-configuration/prod', video_id, query={
                'programme_id': video_id,
                'signed': '0',
                'lang': 'en',
                'mode': 'od',
                'appId': 'clic',
                'streamName': '',
            }, note='Downloading player config JSON')
        thumbnail = playerConfig['poster']
        subtitlesList = playerConfig['subtitles']
        subtitles = {}

        for i in subtitlesList:
            subtitles[i['3']] = [{'url': i['0']}]

        filename = playerConfig['filename']
        m3u8_url = self._download_json(
            'https://player-api.s4c-cdn.co.uk/streaming-urls/prod', video_id, query={
                'mode': 'od',
                'application': 'clic',
                'region': 'WW',
                'extra': 'false',
                'thirdParty': 'false',
                'filename': filename,
            }, note='Downloading streaming urls JSON')['hls']
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': thumbnail,
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
            'description': 'md5:e878ebf660dce89bd2ef521d7ce06397'
        },
    }, {
        'url': 'https://www.s4c.cymru/clic/series/866852587',
        'playlist_mincount': 8,
        'info_dict': {
            'id': '866852587',
            'title': 'FFIT Cymru',
            'description': 'md5:abcb3c129cb68dbb6cd304fd33b07e96'
        },
    }]

    def _real_extract(self, url):
        series_id = self._match_id(url)
        seriesDetails = self._download_json(
            'https://www.s4c.cymru/df/series_details', series_id, query={
                'lang': 'e',
                'series_id': series_id,
                'show_prog_in_series': 'Y'
            }, note='Downloading player config JSON')
        episodes = (self.url_result(
                    'https://www.s4c.cymru/clic/programme/%s' % episode['id'],
                    video_id=episode['id'])
                    for episode in traverse_obj(seriesDetails, ('other_progs_in_series')))

        return self.playlist_result(
            entries=episodes,
            playlist_id=series_id,
            **traverse_obj(seriesDetails, ('full_prog_details', 0, {
                'title': (('series_title'), {str}),
                'description': ('full_billing', {str.strip}),
            }), get_all=False))
