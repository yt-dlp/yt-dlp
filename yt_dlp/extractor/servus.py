from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    unified_timestamp,
    urlencode_postdata,
    url_or_none,
)


class ServusIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:
                            servus\.com/(?:(?:at|de)/p/[^/]+|tv/videos)|
                            (?:servustv|pm-wissen)\.com/[^/]+/v
                        )
                        /(?P<id>[aA]{2}-?\w+|\d+-\d+)
                    '''
    _TESTS = [{
        # new URL schema
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
        # old URL schema
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
        format_url = url_or_none(video.get('videoUrl'))
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            format_url, video_id, 'mp4', entry_protocol='m3u8_native',
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
