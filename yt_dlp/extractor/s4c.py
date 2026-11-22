from .common import InfoExtractor
from ..utils import (
    str_or_none,
    unified_strdate,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class S4CIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?s4c\.cymru/clic/programme/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.s4c.cymru/clic/programme/893068169',
        'info_dict': {
            'id': '893068169',
            'ext': 'mp4',
            'title': 'Uchafbwyntiau',
            'description': 'md5:5d7c0e28213d7e0871b8e9ef8a67a5fe',
            'duration': 900,
            'thumbnail': 'https://www.s4c.cymru/amg/1920x1080/Pride_2024S4C-P11_Uchafbwyntiau-0608.jpg',
            'upload_date': '20240701',
            'release_date': '20240717',
            'series': 'Pride Cymru 2024',
            'series_id': '893067960',
        },
    }, {
        # Geo restricted to the UK
        'url': 'https://www.s4c.cymru/clic/programme/947426692',
        'info_dict': {
            'id': '947426692',
            'ext': 'mp4',
            'title': 'Bwyd a Diod',
            'description': 'md5:9d33c3099b93884d946575f4b77fce27',
            'duration': 1380,
            'thumbnail': 'https://www.s4c.cymru/amg/1920x1080/3can_2026S4C_Brand_001.jpg',
            'upload_date': '20260513',
            'release_date': '20260521',
            'series': '3 Can',
            'series_id': '947426687',
        },
    }, {
        # No series
        'url': 'https://www.s4c.cymru/clic/programme/876045439',
        'info_dict': {
            'id': '876045439',
            'ext': 'mp4',
            'title': 'Ffa Coffi Pawb!',
            'description': 'md5:d1ccbb61c4233b3a443cc092f45bc193',
            'duration': 3240,
            'thumbnail': 'https://www.s4c.cymru/amg/1920x1080/Ffa_Coffi_Pawb_2024S4C_001.jpg',
            'upload_date': '20260131',
            'release_date': '20260131',
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
                'region': 'UK' if player_config.get('application') == 's4chttpl' else 'WW',
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
                'upload_date': ('clic_aired', {unified_strdate}),
                'release_date': ('last_tx', {unified_strdate}),
                'series': ('series_title', {str}, filter),
                'series_id': ('series_id', {str_or_none}, filter),
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
