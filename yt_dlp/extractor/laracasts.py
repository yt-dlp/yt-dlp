import json

from .common import InfoExtractor
from .mux import MuxIE
from ..utils import (
    clean_html,
    int_or_none,
    parse_duration,
    str_or_none,
    unified_strdate,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj
from bs4 import BeautifulSoup

chapter_names = []

chapter_episodes_counts = []

chapters_count = 0

def set_episode_chapter_info(episode):
    global chapter_names
    global chapters_count
    global chapter_episodes_counts
    index = int(episode['chapter']) - 1
    episode['chapterName'] = chapter_names[index]
    episode['chaptersCount'] = chapters_count
    episode['chapterEpisodesCount'] = chapter_episodes_counts[index]
    return episode

def get_chapter_info(chapter):
    global chapter_names
    global chapter_episodes_counts
    index = int(chapter['number']) - 1
    chapter_names[index] = chapter['heading']
    chapter_episodes_counts[index] = chapter['count']
    return chapter

def get_relative_episode_number(episode_number):
    global chapter_episodes_counts
    relative_episode_number = episode_number
    increment = 0
    for episodes_count in chapter_episodes_counts:
        if increment + episodes_count >= episode_number:
            relative_episode_number = episode_number - increment
            break
        increment = increment + episodes_count
    return relative_episode_number



class LaracastsBaseIE(InfoExtractor):
    def _get_prop_data(self, url, display_id):
        webpage = self._download_webpage(url, display_id)
        soup = BeautifulSoup(webpage, 'lxml')
        return traverse_obj(
            soup.find('script', {'data-page': 'app'}).text,
            ({json.loads}, 'props'))

    def _parse_episode(self, episode):
        with open(r'C:\Users\Osema\Music\test\laracasts\test.json', 'w') as f:
            f.write(json.dumps(episode))
        if not traverse_obj(episode, 'muxPlaybackId'):
            self.raise_login_required('This video is only available for subscribers.')
        return self.url_result(
            f'https://player.mux.com/{episode["muxPlaybackId"]}?playback-token={episode['muxTokens']['playback']}',
            MuxIE, url_transparent=True,
            **traverse_obj(episode, {
                'id': ('id', {int}, {str_or_none}),
                'webpage_url': ('path', {urljoin('https://laracasts.com')}),
                'title': ('title', {clean_html}),
                'chapter_number': ('chapter', {int_or_none}),
                'chapter_name': ('chapterName', {str_or_none}),
                'chapters_count': ('chaptersCount', {int_or_none}),
                'chapter_episodes_count': ('chapterEpisodesCount', {int_or_none}),
                'episode_number': ('position', {int_or_none}),
                'relative_episode_number': ('position', {get_relative_episode_number}),
                'description': ('body', {clean_html}),
                'thumbnail': ('largeThumbnail', {url_or_none}),
                'duration': ('length', {int_or_none}),
                'upload_date': ('dateSegments', 'published', {unified_strdate}),
            }))


class LaracastsIE(LaracastsBaseIE):
    IE_NAME = 'laracasts'
    _VALID_URL = r'https?://(?:www\.)?laracasts\.com/series/(?P<id>[\w-]+/episodes/\d+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://laracasts.com/series/30-days-to-learn-laravel-11/episodes/1',
        'md5': 'c8f5e7b02ad0e438ef9280a08c8493dc',
        'info_dict': {
            'id': '922040563',
            'title': 'Hello, Laravel',
            'ext': 'mp4',
            'duration': 519,
            'upload_date': '20240312',
            'thumbnail': 'https://laracasts.s3.amazonaws.com/videos/thumbnails/youtube/30-days-to-learn-laravel-11-1.png',
            'description': 'md5:ddd658bb241975871d236555657e1dd1',
            'season_number': 1,
            'season': 'Season 1',
            'episode_number': 1,
            'episode': 'Episode 1',
            'uploader': 'Laracasts',
            'uploader_id': 'user20182673',
            'uploader_url': 'https://vimeo.com/user20182673',
        },
        'expected_warnings': ['Failed to parse XML'],  # TODO: Remove when vimeo extractor is fixed
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        props = self._get_prop_data(url, display_id)
        lesson = props['lesson']
        chapters = props['series']['chapters']
        index = int(lesson['chapter']) - 1
        lesson['chapterName'] = chapters[index]['heading']
        lesson['chaptersCount'] = len(chapters)
        global chapter_episodes_counts
        chapter_episodes_counts = [int(c['count']) for c in chapters]
        lesson['chapterEpisodesCount'] = chapter_episodes_counts[index]
        return self._parse_episode(lesson)


class LaracastsPlaylistIE(LaracastsBaseIE):
    IE_NAME = 'laracasts:series'
    _VALID_URL = r'https?://(?:www\.)?laracasts\.com/series/(?P<id>[\w-]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://laracasts.com/series/30-days-to-learn-laravel-11',
        'info_dict': {
            'title': '30 Days to Learn Laravel',
            'id': '210',
            'thumbnail': 'https://laracasts.s3.amazonaws.com/series/thumbnails/social-cards/30-days-to-learn-laravel-11.png?v=2',
            'duration': 30600.0,
            'modified_date': '20240511',
            'description': 'md5:27c260a1668a450984e8f901579912dd',
            'categories': ['Frameworks'],
            'tags': ['Laravel'],
            'display_id': '30-days-to-learn-laravel-11',
        },
        'playlist_count': 30,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        series = self._get_prop_data(url, display_id)['series']

        global chapter_names

        global chapters_count

        global chapter_episodes_counts

        chapters_count = len(series['chapters'])

        chapter_names = ['' for i in range(chapters_count)]
        chapter_episodes_counts = [0 for i in range(chapters_count)]

        metadata = {
            'display_id': display_id,
            **traverse_obj(series, {
                'title': ('title', {str}),
                'id': ('id', {int}, {str_or_none}),
                'description': ('body', {clean_html}),
                'thumbnail': (('large_thumbnail', 'thumbnail'), {url_or_none}, any),
                'duration': ('runTime', {parse_duration}),
                'categories': ('taxonomy', 'name', {str}, all, filter),
                'tags': ('topics', ..., 'name', {str}),
                'modified_date': ('lastUpdated', {unified_strdate}),
            }),
        }

        return self.playlist_result(traverse_obj(
            series, ('chapters', lambda _,v: get_chapter_info(v) , 'episodes', lambda _, v: set_episode_chapter_info(v), {self._parse_episode})), **metadata)

