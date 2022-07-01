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
                        /(?P<id>[aA]{2}-?\w+|\d+-\d+)
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
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video.get('videoUrl'), video_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls', fatal=False)
        thumbnail = video.get("poster")
        self._sort_formats(formats)

        title = video.get("title") or video_id
        description = video.get('description')
        series = video.get("label")
        season = video.get('season')
        episode = video.get('chapter')
        duration = float_or_none(video.get('duration'))
        season_number = int_or_none(self._search_regex(
            r'Season (\d+)', season or '', 'season number', default=None))
        episode_number = int_or_none(self._search_regex(
            r'Episode (\d+)', episode or '', 'episode number', default=None))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': unified_timestamp(video.get('currentSunrise')),
            'series': series,
            'season': season,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'formats': formats,
            'subtitles': subtitles,
        }
