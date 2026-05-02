import json
from html.parser import HTMLParser

from .common import InfoExtractor
from .mux import MuxIE
from ..utils import (
    clean_html,
    int_or_none,
    parse_duration,
    str_or_none,
    unified_strdate,
    url_or_none,
    urljoin
)

from ..utils.traversal import traverse_obj


class LaracastsParser(HTMLParser):

    def __init__(self, *, convert_charrefs=True):
        super().__init__(convert_charrefs=convert_charrefs)
        self.is_data_page_script = False
        self.json_content = ''

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if (tag.lower() == 'script' and attributes.get('type', '') == 'application/json' and
                attributes.get('data-page', '') == 'app'):

            self.is_data_page_script = True

    def handle_data(self, data):
        if self.is_data_page_script:
            self.json_content += data

    def handle_endtag(self, tag):
        if tag.lower() == 'script':
            self.is_data_page_script = False

class LaracastsChapterInfo:

    def __init__(self, props):
        chapters = props['series']['chapters']
        self.__chapters_count = len(chapters)
        self.__chapter_names = [chapter['heading'] for chapter in chapters]
        self.__chapter_episodes_counts = [int(chapter['count']) for chapter in chapters]

    def __get_relative_episode_number(self, episode_number):
        relative_episode_number = episode_number
        increment = 0
        for v in self.__chapter_episodes_counts:
            if v >= episode_number:
                break
            if increment + v >= episode_number:
                relative_episode_number = episode_number - increment
                break
            increment += v
        return relative_episode_number

    def add_to_episode(self, episode):
        chapter_index = int(episode['chapter']) - 1
        episode['chapterName'] = self.__chapter_names[chapter_index]
        episode['chapterEpisodesCount'] = self.__chapter_episodes_counts[chapter_index]
        episode['relativeEpisodeNumber'] = self.__get_relative_episode_number(episode['position'])
        episode['chaptersCount'] = self.__chapters_count
        return episode


class LaracastsBaseIE(InfoExtractor):
    def _get_prop_data(self, url, display_id):
        webpage = self._download_webpage(url, display_id)

        parser = LaracastsParser()
        parser.feed(webpage)
        parser.close()

        return traverse_obj(
            parser.json_content,
            ({json.loads}, 'props'))

    def _parse_episode(self, episode):
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
                'relative_episode_number': ('relativeEpisodeNumber', {int_or_none}),
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

        chapter_info = LaracastsChapterInfo(props)

        return self._parse_episode(chapter_info.add_to_episode(props['lesson']))


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
        props = self._get_prop_data(url, display_id)

        series = props['series']

        chapter_info = LaracastsChapterInfo(props)

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
            series, ('chapters', ..., 'episodes', lambda _, v: chapter_info.add_to_episode(v), {self._parse_episode})),
            **metadata)
