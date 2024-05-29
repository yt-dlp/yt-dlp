from .common import InfoExtractor
from .vimeo import VimeoIE
from ..utils import (
    extract_attributes,
    get_element_html_by_id,
)


class LaracastsPlaylistIE(InfoExtractor):
    IE_NAME = 'laracasts:series'
    _VALID_URL = r'https?://(?:www\.)?laracasts\.com/series/(?P<series>[^/?#]+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://laracasts.com/series/30-days-to-learn-laravel-11',
        'info_dict': {
            'title': '30 Days to Learn Laravel',
            'id': 210,
        },
        'only_matching': True,
    }]

    def _entries(self, series, episode_count):
        for current_episode in range(1, episode_count + 1):
            webpage_url = f'https://laracasts.com/series/{series}/episodes/{current_episode}'
            yield self.url_result(webpage_url, LaracastsIE)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('series')
        webpage = self._download_webpage(url, display_id)
        episode_count = int(self._search_regex(r'episodeCount&quot;:(?P<episode_count>[0-9]+)', webpage, 'episode_count'))
        playlist_title = self._search_regex(r'title&quot;:&quot;(?P<playlist_title>[^&]+)&quot;,', webpage, 'playlist_title')
        playlist_id = self._search_regex(r'id&quot;:(?P<playlist_id>[0-9]+)', webpage, 'playlist_id')
        return self.playlist_result(self._entries(display_id, episode_count), playlist_id, playlist_title)


class LaracastsIE(InfoExtractor):
    IE_NAME = 'laracasts'
    _VALID_URL = r'https?://(?:www\.)?laracasts\.com/series/(?P<series>[\w\d-]+)/episodes/(?P<episode_number>[0-9]+)$'
    _TESTS = [{
        'url': 'https://laracasts.com/series/30-days-to-learn-laravel-11/episodes/1',
        'md5': 'c8f5e7b02ad0e438ef9280a08c8493dc',
        'info_dict': {
            'id': '922040563',
            'title': '1-Hello-Laravel',
            'uploader': 'Laracasts',
            'uploader_id': 'user20182673',
            'uploader_url': 'https://vimeo.com/user20182673',
            'ext': 'mp4',
            'duration': 519,
            'thumbnail': 'https://i.vimeocdn.com/video/1812897371-64aac3913bc92e99c5a56ff58fa0d4894993ba04bd2e6703d3f2295e998d5548-d_1280',
        }
    }]

    def extract_vimeo_id(self, url):
        mobj = self._match_valid_url(url)

        series, episode_number = mobj.group('series', 'episode_number')
        display_id = '%s/%s' % (series, episode_number)

        webpage = self._download_webpage(url, display_id)
        app_element = get_element_html_by_id('app', webpage)
        app_attributes = extract_attributes(app_element)
        app_json = self._parse_json(app_attributes.get('data-page'), display_id)
        series_chapters = app_json['props']['series']['chapters']

        for chapter in series_chapters:
            for episode in chapter['episodes']:
                if int(episode['position']) == int(episode_number):
                    return episode['vimeoId']

    def _real_extract(self, url):
        video_id = self.extract_vimeo_id(url)
        embed_url = VimeoIE._smuggle_referrer(f'https://player.vimeo.com/video/{video_id}', 'https://laracasts.com/')

        return self.url_result(embed_url)
