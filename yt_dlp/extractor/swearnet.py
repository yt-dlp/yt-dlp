from .common import InfoExtractor
from ..utils import int_or_none


class SwearnetShowIE(InfoExtractor):
    _VALID_URL = r'https?://www\.swearnet\.com/shows/(?P<id>[\w-]+)/seasons/(?P<season_num>\d+)/episodes/(?P<episode_num>\d+)'
    _TESTS = [{
        'url': 'https://www.swearnet.com/shows/gettin-learnt-with-ricky/seasons/1/episodes/1',
        'info_dict': {
            'id': '232819',
            'ext': 'mp4',
            'episode_number': 1,
            'episode': 'Episode 1',
            'duration': 719,
            'description': 'md5:c48ef71440ce466284c07085cd7bd761',
            'season': 'Season 1',
            'title': 'Episode 1 - Grilled Cheese Sammich',
            'season_number': 1,
        }
    }]

    def _get_formats_and_subtitle(self, video_source, video_id):
        formats, subtitles = [], {}
        for key, value in video_source.items():
            if key == 'mp4':
                for video_mp4 in value:
                    fmts = [{
                        'url': video_mp4.get('url'),
                        'ext': 'mp4'
                    }]
                    formats.extend(fmts)

            elif key == 'hls':
                for video_hls in value:
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(video_hls.get('url'), video_id)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
        return formats, subtitles

    def _real_extract(self, url):
        display_id, season_number, episode_number = self._match_valid_url(url).group('id', 'season_num', 'episode_num')
        webpage = self._download_webpage(url, display_id)

        external_id = self._search_regex(r'externalid\s*=\s*"([^"]+)', webpage, 'externalid')

        # vidyard player request
        json_data = self._download_json(
            f'https://play.vidyard.com/player/{external_id}.json', display_id)['payload']['chapters'][0]

        formats, subtitles = self._get_formats_and_subtitle(json_data['sources'], display_id)

        return {
            'id': str(json_data['videoId']),
            'title': json_data.get('name'),
            'description': json_data.get('description'),
            'duration': int_or_none(json_data.get('seconds')),
            'formats': formats,
            'subtitles': subtitles,
            'season_number': int_or_none(season_number),
            'episode_number': int_or_none(episode_number),
        }
