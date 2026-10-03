from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    format_field,
    int_or_none,
    merge_dicts,
    traverse_obj,
    unescapeHTML,
    unified_timestamp,
)


class ServusIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:
                            servus\.com/(?:(?:at|de)/p/[^/]+|tv/videos)|
                            (?:servustv|pm-wissen)\.com/(?:[^/]+/)?(?:v(?:ideos)?|(?:at|de)/page)
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
            'description': 'md5:86d0c9eb3b2b6d7cdff247d1ba997ace',
            'thumbnail': r're:^https?://.*',
            'duration': 2823280.0,
            'timestamp': 1655752333,
            'upload_date': '20220620',
            'series': 'Bergwelten',
            'season': 'Season 11',
            'season_number': 11,
            'episode': 'Episode 8 - Vie Ferrate – Klettersteige in den Alpen',
            'episode_number': 8,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.servustv.com/natur/v/aa-1xg5xwmgw2112/',
        'only_matching': True,
    }, {
        'url': 'https://www.servustv.com/natur/v/aansszcx3yi9jmlmhdc1/',
        'only_matching': True,
    }, {
        # URL schema v2
        'url': 'https://www.servustv.com/videos/aa-1t6vbu5pw1w12/',
        'only_matching': True,
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
        webpage, urlh = self._download_webpage_handle(url, video_id)
        video_id = self._match_id(urlh.url).upper()
        next_data = {}
        next_datas = traverse_obj(
            self._search_nextjs_v13_data(webpage, video_id, fatal=False),
            (..., 'featuredCollectionCards', lambda _, x: video_id in x.get('id'), {dict}),
        )
        if next_datas:
            next_data = merge_dicts(*next_datas)
        video = self._download_json(
            'https://api-player.redbull.com/tv', video_id, 'Downloading video JSON',
            query={'videoId': video_id, 'tenant': 'stv', 'locale': 'de'},
        )
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
            'description': unescapeHTML(next_data.get('long_description')) or video.get('description'),
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
            **traverse_obj(next_data, {
                'title': ('title', {str}),
                'duration': ('duration', {float_or_none}),
            }),
        }

    def _report_errors(self, video):
        playability_errors = traverse_obj(video, ('playabilityErrors', ...))
        if not playability_errors:
            raise ExtractorError('No videoUrl and no information about errors')

        elif 'FSK_BLOCKED' in playability_errors:
            details = traverse_obj(video, ('playabilityErrorDetails', 'FSK_BLOCKED'), expected_type=dict)
            message = format_field(''.join((
                format_field(details, 'minEveningHour', ' from %02d:00'),
                format_field(details, 'maxMorningHour', ' to %02d:00'),
                format_field(details, 'minAge', ' (Minimum age %d)'),
            )), None, 'Only available%s') or 'Blocked by FSK with unknown availability'

        elif 'NOT_YET_AVAILABLE' in playability_errors:
            message = format_field(
                video, (('playabilityErrorDetails', 'NOT_YET_AVAILABLE', 'availableFrom'), 'currentSunrise'),
                'Only available from %s') or 'Video not yet available with unknown availability'

        else:
            message = f'Video unavailable: {", ".join(playability_errors)}'

        raise ExtractorError(message, expected=True)
