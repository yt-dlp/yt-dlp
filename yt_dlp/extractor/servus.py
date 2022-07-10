from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    unified_timestamp,
)


class ServusIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:
                            servus\.com/(?:(?:at|de)/p/[^/]+|tv/videos)|
                            (?:servustv|pm-wissen)\.com/(?:[^/]+/)?v(?:ideos)?
                        )
                        /(?P<id>((AA|aa)-[A-Za-z0-9]{13})|([0-9]+-[0-9]+)|([A-Za-z]{2}[0-9A-Za-z]{18}))
                    '''
    _TESTS = [{
        'url': 'https://www.servustv.com/natur/v/aa-28bycqnh92111/',
        'info_dict': {
            'id': 'AA-28BYCQNH92111',
            'ext': 'mp4',
            'title': 'Klettersteige in den Alpen',
            'description': 'md5:bab622a45e44872fdaea7f90b56f0ce8',
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
        'url': 'https://www.pm-wissen.com/videos/aa-24mus4g2w2112/',
        'only_matching': True,
    }, {
        'url': 'https://www.servustv.com/natur/v/aa-1xg5xwmgw2112/',
        'only_matching': True,
    }, {
        'url': 'https://www.servustv.com/natur/v/aansszcx3yi9jmlmhdc1/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).upper()

        video = self._download_json(
            'https://api-player.redbull.com/stv/servus-tv?timeZone=Europe/Berlin&videoId=%s' % video_id,
            video_id, 'Downloading video JSON')
        if 'videoUrl' not in video:
            self._report_errors(video)
            return None
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video['videoUrl'], video_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')
        self._sort_formats(formats)

        season = video.get('season')
        season_number = int_or_none(self._search_regex(
            r'Season (\d+)', season or '', 'season number', default=None))
        episode = video.get('chapter')
        episode_number = int_or_none(self._search_regex(
            r'Episode (\d+)', episode or '', 'episode number', default=None))

        return {
            'id': video_id,
            'title': video.get('title'),
            'description': self._get_description(video, video_id),
            'thumbnail': video.get('poster'),
            'duration': float_or_none(video.get('duration')),
            'timestamp': unified_timestamp(video.get('currentSunrise')),
            'series': season,
            'season': video.get('season'),
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'formats': formats,
            'subtitles': subtitles,
        }


    def _get_description(self, video, video_id):
        info = self._download_json("https://backend.servustv.com/wp-json/rbmh/v2/media_asset/aa_id/%s?fieldset=page" % video_id,
                                   video_id, fatal=False)
        if not info:
            return video.get('description')
        description = info.get('stv_long_description') \
            or info.get("stv_short_description") \
            or video.get('description')
        return description

    def _report_errors(self, video):
        if 'playabilityErrors' not in video:
            self.report_warning('No videoUrl, and also no information about errors')
        for error in video.get('playabilityErrors'):
            if error == 'FSK_BLOCKED':
                details = video['playabilityErrorDetails']['FSK_BLOCKED']
                if 'minEveningHour' in details:
                    self.report_warning('Only playable from '
                                        + f'{details["minEveningHour"]}:00 to '
                                        + f'{details["maxMorningHour"]}:00')
            elif error == 'NOT_YET_AVAILABLE':
                self.report_warning('Only available after '
                                    + video.get('currentSunrise'))
            else:
                self.report_warning(f'Not playable: {error}')
