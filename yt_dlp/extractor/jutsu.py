from yt_dlp.utils import determine_ext
from .common import InfoExtractor
from pprint import pprint
import re

def create_formats_from_episode_info(episode_info):
    return [ {'url': episode_info['url'], 'ext': determine_ext(episode_info['url']), 'thumbnail': episode_info['thumbnail']} ]

def create_result_from_episode_info(episode_info, id):
    return {
            'formats': create_formats_from_episode_info(episode_info),
            'id': id,
            'title': episode_info['title'],
    }

def parse_episode(webpage, extractor):
    source = extractor._html_search_regex(r"<source\s+src=\"([^\"]+)\"", webpage, "video links")
    title = extractor._search_regex(r'(?<=<i>)Смотреть <\/i>(.*)<\/span>', webpage, 'title')
    thumbnail = extractor._search_regex(r'poster="([^"]+)"', webpage, 'thumbnail')

    return {
        'url': source, 
        'ext': determine_ext(source), 
        'thumbnail': thumbnail,
        'title': title,
    }

class JutSuAnimeIE(InfoExtractor):
    _VALID_URL = r'https:\/\/jut\.su\/(?P<name>[\w-]+)\/?'

    def _real_extract(self, url):
        anime_name = self._match_valid_url(url).group('name')

        episodes = []

        webpage = self._download_webpage(url, anime_name)

        fr = re.findall(r'<a\s+href=\"(?P<href>[^\"]+)\"\s+class=\".+?\s+video\s+the_hildi\">', webpage)
        links = [f'https://jut.su{i}' for i in fr]

        for i, link in enumerate(links):
            episode_id = anime_name + str(i + 1)
            episode_webpage = self._download_webpage(link, episode_id)
            parsed = parse_episode(episode_webpage, self)
            episodes.append(create_result_from_episode_info(parsed, episode_id))

        return self.playlist_result(episodes, anime_name)
        

class JutSuEpisodeIE(InfoExtractor):
    _VALID_URL = r'https:\/\/jut\.su\/(?P<name>[\w-]+)\/(?:season-(?P<season>[1-9])+)?\/?(?:episode-(?P<episode>[1-9]+))\.html' # https://regex101.com/r/HY9Z6F/1
    _TESTS = [
        {
            'url': 'https://jut.su/kaze-no-stigma/episode-9.html',
            'info_dict': {
                'ext': 'mp4',
                'id': 'kaze-no-stigma-None-9',
                'title': 'Печать ветра 9 серия',
                'thumbnail': r're:^https?://.*\.jpg$'
            }
        }
    ]

    def _real_extract(self, url):
        episode = self._match_valid_url(url).group('episode')
        season = self._match_valid_url(url).group('season')
        anime_name = self._match_valid_url(url).group('name')

        video_id = f'{anime_name}-{season}-{episode}'
        webpage = self._download_webpage(url, video_id)

        parsed = parse_episode(webpage, self)

        return create_result_from_episode_info(parsed, video_id)
        
