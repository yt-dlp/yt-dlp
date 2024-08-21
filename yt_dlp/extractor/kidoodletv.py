import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    js_to_json,
    merge_dicts,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)


class KidoodleTVBaseIE(InfoExtractor):
    def _extract_data(self, webpage, video_id):
        keys = self._html_search_regex(r'__NUXT__=\(function\(([^\)]+)\)\{', webpage, 'key', default=None)
        key_list = self._parse_json(js_to_json(f'[{keys}]'), video_id, fatal=False)
        data = self._html_search_regex(r'\}\}\}\((".+)\)\);</script>', webpage, 'data', default=None)
        data_list = self._parse_json(js_to_json(f'[{data}]'), video_id, fatal=False)
        data_set = {}
        if key_list and data_list and (len(data_list) == len(key_list)):
            for idx, key in enumerate(key_list):
                data_set[key] = data_list[idx]
        return data_set

    def _extract_by_idx(self, idx, webpage, data, display_id=None):
        def slugify(string):
            s = string.lower().strip()
            s = re.sub(r'[0-9]', '', s)
            s = re.sub(r'[^\w\s-]', '', s)
            s = re.sub(r'[\s_-]+', '-', s)
            return re.sub(r'^-+|-+$', '', s)

        def get_field(field_name, idx, webpage, data):
            value = self._html_search_regex(rf'{idx}\.{field_name}=(?P<a>"?(?P<b>.+?)"?);', webpage,
                                            field_name, default=None, group=('a', 'b'))
            return (value[1] if value[1] != value[0] else (
                    data.get(value[0]) if re.search(r'^[a-zA-Z_\$]{1,4}$', value[0]) else value[0]))

        idx = idx.replace('$', r'\$')
        video_id = get_field('id', idx, webpage, data)
        title = get_field('title', idx, webpage, data)
        brief = get_field('shortSummary', idx, webpage, data) or ''
        summary = get_field('summary', idx, webpage, data) or ''
        description = (summary if brief[:-3] in summary else join_nonempty(brief, summary, delim='\n')
                       ).replace(r'\"', '"')
        series = get_field('seriesName', idx, webpage, data)
        season_episode = get_field('seasonAndEpisode', idx, webpage, data)
        season, episode = self._search_regex(r'^S(?P<season>\d+)E(?P<episode>\d+)', season_episode,
                                             'season_episode', group=('season', 'episode'))
        if release_date := get_field('premiere_date', idx, webpage, data):
            release_date = release_date.replace('-', '')
        duration = get_field('duration', idx, webpage, data)
        thumbnails, formats, subtitles = [], [], {}
        if images := self._html_search_regex(rf'{idx}\.images=(\[[^\]]+]);', webpage,
                                             'images', default=None):
            for image_url in traverse_obj(self._parse_json(js_to_json(images), video_id, fatal=False),
                                          (..., 'url', {lambda v: url_or_none(v.replace('\\u002F', '/'))})):
                if determine_ext(image_url) != 'mp4':
                    thumbnails.append({
                        'url': image_url,
                        'preference': -1 if '_large' in image_url else -2,
                    })
        if video_url := get_field('videoUrl', idx, webpage, data):
            video_url = video_url.replace('\\u002F', '/')
            if determine_ext(video_url) == 'm3u8':
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id)
        return {
            'id': video_id,
            'display_id': display_id or f'{season_episode}-{slugify(title)}',
            'title': title,
            'description': description,
            'thumbnails': thumbnails,
            'release_date': release_date,
            'series': series,
            'season_number': int_or_none(season),
            'episode_number': int_or_none(episode),
            'duration': float_or_none(duration),
            'formats': formats,
            'subtitles': subtitles,
        }


class KidoodleTVIE(KidoodleTVBaseIE):
    _VALID_URL = r'https?://kidoodle\.tv/(?P<series_id>\d+)/(?P<series>[^/]+)/(?P<id>(?P<season_episode>S\d+E\d+)[^/\?]*)'
    _TESTS = [{
        'url': 'https://kidoodle.tv/2376/regal-academy/S1E01-a-school-for-fairy-tales',
        'info_dict': {
            'id': '84499',
            'ext': 'mp4',
            'display_id': 'S1E01-a-school-for-fairy-tales',
            'title': 'A School for Fairy Tales',
            'description': 'md5:4083278308ce6dda1660445b5073b851',
            'thumbnail': 'https://imgcdn.kidoodle.tv/RegalAcademy/S01/keyart_e01_large.jpg',
            'release_date': '20160521',
            'series': 'Regal Academy',
            'series_id': '2376',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'duration': 1423.4,
        },
    }, {
        'url': 'https://kidoodle.tv/3083/unicorn-academy/S1E04-fun-with-foals',
        'info_dict': {
            'id': '105372',
            'ext': 'mp4',
            'display_id': 'S1E04-fun-with-foals',
            'title': 'Fun with Foals',
            'description': 'The Sapphire team looks after a newborn baby unicorn!',
            'thumbnail': 'https://imgcdn.kidoodle.tv/UnicornAcademy/S01/keyart_e04_large.jpg',
            'release_date': '20231027',
            'series': 'Unicorn Academy',
            'series_id': '3083',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 4',
            'episode_number': 4,
            'duration': 746.816,
        },
    }]

    def _real_extract(self, url):
        video_id, series_id, series, season_episode = self._match_valid_url(url).group(
            'id', 'series_id', 'series', 'season_episode')
        webpage = self._download_webpage(f'https://kidoodle.tv/{series_id}/{series}', video_id,
                                         fatal=False, expected_status=(404, 500))
        if 'Server error' in webpage or 'Something went wrong' in webpage:
            qs = urlencode_postdata({'origin': urllib.parse.urlparse(url).path})
            self._download_webpage(f'https://kidoodle.tv/welcome?{qs}', video_id, note='Downloading welcome page')
            self._download_webpage(f'https://kidoodle.tv/welcome/verify?{qs}', video_id, note='Performing age verification')
            # the above lines download the webpages to change verification status, not really get verified
            webpage = self._download_webpage(url, video_id)

        description = self._html_search_meta('description', webpage, 'description', default=None)
        data_set = self._extract_data(webpage, video_id)
        info = {}
        if idx := self._html_search_regex(rf'([\w\$]{{1,4}})\.seasonAndEpisode="{season_episode}";',
                                          webpage, 'data_idx', default=None):
            info = self._extract_by_idx(idx, webpage, data_set, video_id)

        return merge_dicts(info, {
            'id': video_id,
            'description': description,
            'series_id': series_id,
        })


class KidoodleTVSeriesIE(KidoodleTVBaseIE):
    _VALID_URL = r'https?://kidoodle\.tv/(?P<id>\d+)/(?P<slug>[\w-]+)[^/]*/?$'
    IE_NAME = 'KidoodleTV:series'
    _TESTS = [{
        'url': 'https://kidoodle.tv/3014/bluey-the-videogame-by-abdallah-smash',
        'info_dict': {
            'id': '3014',
            'title': 'Bluey: The Videogame by Abdallah Smash',
            'description': 'Bluey: The Videogame on Nintendo Switch with no-commentary.',
        },
        'playlist_count': 8,
    }, {
        'url': 'https://kidoodle.tv/3083/unicorn-academy?category=What%27s%20NEW',
        'info_dict': {
            'id': '3083',
            'title': 'Unicorn Academy',
            'description': 'md5:d3f92c6bd76cc9941e60d827213b79f3',
        },
        'playlist_count': 4,
    }]

    def _real_extract(self, url):
        series_id, slug = self._match_valid_url(url).group('id', 'slug')
        webpage = self._download_webpage(url, series_id)

        title = self._html_search_regex(r'<h2[^>]+>(.*?)</h2>', webpage, 'title', default=None)
        description = self._html_search_regex(r'<p class="mb[^>]+>(.*?)</p>', webpage,
                                              'description', default=None)
        data_set = self._extract_data(webpage, series_id)
        entries = []
        for idx_se in sorted(re.findall(r'([\w\$]{1,4})\.seasonAndEpisode="([^"]+)";', webpage),
                             key=lambda x: x[1]):
            if entry := self._extract_by_idx(idx_se[0], webpage, data_set):
                entry['series_id'] = series_id
                entry['webpage_url'] = join_nonempty('https://kidoodle.tv', series_id, slug,
                                                     entry['display_id'], delim='/')
                entry['webpage_url_basename'] = entry['display_id']
                entries.append(entry)

        return self.playlist_result(entries, series_id, title, description)
