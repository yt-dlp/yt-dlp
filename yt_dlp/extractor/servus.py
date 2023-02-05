from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    traverse_obj,
    unified_timestamp,
    unescapeHTML,
)


class ServusIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:
                            servus\.com/(?:(?:at|de)/p/[^/]+|tv/videos)|
                            (?:servustv|pm-wissen)\.com/(?:[^/]+/)?v(?:ideos)?
                        )
                        /(?P<id>[aA]{2}-?\w+|\d+-\d+)
                    '''
    _TESTS = [{
        # URL schema v3
        'url': 'https://www.servustv.com/natur/v/aa-28bycqnh92111/',
        'info_dict': {
            'id': 'AA-28BYCQNH92111',
            'ext': 'mp4',
            'title': 'Klettersteige in den Alpen',
            'description': 'md5:6f681e794bb41ebddd5c3de7d2717a68',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2823,
            'timestamp': 1655752333,
            'upload_date': '20220620',
            'series': 'Bergwelten',
            'season': 'Season 11',
            'season_number': 11,
            'episode': 'Episode 8 - Vie Ferrate – Klettersteige in den Alpen',
            'episode_number': 8,
        },
        'params': {'skip_download': 'm3u8'}
    }, {
        'url': 'https://www.servustv.com/natur/v/aa-1xg5xwmgw2112/',
        'only_matching': True,
    }, {
        'url': 'https://www.servustv.com/natur/v/aansszcx3yi9jmlmhdc1/',
        'only_matching': True,
    }, {
        # URL schema v2
        'url': 'https://www.servustv.com/videos/aa-1t6vbu5pw1w12/',
        'md5': '60474d4c21f3eb148838f215c37f02b9',
        'info_dict': {
            'id': 'AA-1T6VBU5PW1W12',
            'ext': 'mp4',
            'title': 'Die Grünen aus Sicht des Volkes',
            'alt_title': 'Talk im Hangar-7 Voxpops Gruene',
            'description': 'md5:1247204d85783afe3682644398ff2ec4',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 62.442,
            'timestamp': 1605193976,
            'upload_date': '20201112',
            'series': 'Talk im Hangar-7',
            'season': 'Season 9',
            'season_number': 9,
            'episode': 'Episode 31 - September 14',
            'episode_number': 31,
        }
    }, {
        # URL schema v1
        'url': 'https://www.servus.com/de/p/Die-Gr%C3%BCnen-aus-Sicht-des-Volkes/AA-1T6VBU5PW1W12/',
        'only_matching': True,
    }, {
        'url': 'https://www.servus.com/at/p/Wie-das-Leben-beginnt/1309984137314-381415152/',
        'only_matching': True,
    }, {
        'url': 'https://www.servus.com/tv/videos/aa-1t6vbu5pw1w12/',
        'only_matching': True,
    }, {
        'url': 'https://www.servus.com/tv/videos/1380889096408-1235196658/',
        'only_matching': True,
    }, {
        'url': 'https://www.pm-wissen.com/videos/aa-24mus4g2w2112/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).upper()

        video = self._download_json(
            'https://api-player.redbull.com/stv/servus-tv?timeZone=Europe/Berlin',
            video_id, 'Downloading video JSON', query={'videoId': video_id})
        if not video.get('videoUrl'):
            self._report_errors(video)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video['videoUrl'], video_id, 'mp4', m3u8_id='hls')

        season = video.get('season')
        season_number = int_or_none(self._search_regex(
            r'Season (\d+)', season or '', 'season number', default=None))
        episode = video.get('chapter')
        episode_number = int_or_none(self._search_regex(
            r'Episode (\d+)', episode or '', 'episode number', default=None))

        return {
            'id': video_id,
            'title': video.get('title'),
            'description': self._get_description(video_id) or video.get('description'),
            'thumbnail': video.get('poster'),
            'duration': float_or_none(video.get('duration')),
            'timestamp': unified_timestamp(video.get('currentSunrise')),
            'series': video.get('label'),
            'season': season,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _get_description(self, video_id):
        info = self._download_json(
            f'https://backend.servustv.com/wp-json/rbmh/v2/media_asset/aa_id/{video_id}?fieldset=page',
            video_id, fatal=False)

        short_description = unescapeHTML(traverse_obj(info, 'stv_short_description', expected_type=str))
        long_description = unescapeHTML(traverse_obj(info, 'stv_long_description', expected_type=str, default=''))
        long_description = long_description.replace('\n\n', '\n')

        if short_description and long_description:
            return f'{short_description}\n\n{long_description}'
        return long_description or short_description

    def _report_errors(self, video):
        playability_errors = traverse_obj(video, ('playabilityErrors', ...))
        if not playability_errors:
            raise ExtractorError('No videoUrl and no information about errors')

        elif 'FSK_BLOCKED' in playability_errors:
            details = traverse_obj(video, ('playabilityErrorDetails', 'FSK_BLOCKED'), expected_type=dict)
            assert isinstance(details, dict) or details is None
            message = ''
            if details:
                if details.get('minEveningHour') is not None:
                    message += f' from {details["minEveningHour"]:0>2}:00'
                if details.get('maxMorningHour') is not None:
                    message += f' to {details["maxMorningHour"]:0>2}:00'
                if message and details.get('minAge') is not None:
                    message += f' (Minimum age {details["minAge"]})'

            message = (
                f'Only available{message}' if message
                else 'Blocked by FSK with unknown availability')

        elif 'NOT_YET_AVAILABLE' in playability_errors:
            available_from = traverse_obj(
                video, ('playabilityErrorDetails', 'NOT_YET_AVAILABLE', 'availableFrom'), 'currentSunrise')
            message = (
                f'Only available from {available_from}' if available_from
                else 'Video not yet available with unknown availability')

        else:
            message = f'Video unavailable: {", ".join(playability_errors)}'

        raise ExtractorError(message, expected=True)
