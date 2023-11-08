from .common import InfoExtractor

from ..utils import (
    extract_attributes,
    get_element_by_class,
    get_element_html_by_class,
    unified_strdate
)


class TheGuardianPodcastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?theguardian\.com/\w+/audio/\d{4}/\w{3}/\d{1,2}/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.theguardian.com/news/audio/2023/nov/03/we-are-just-getting-started-the-plastic-eating-bacteria-that-could-change-the-world-podcast',
        'md5': 'd1771744681789b4cd7da2a08e487702',
        'info_dict': {
            'id': 'we-are-just-getting-started-the-plastic-eating-bacteria-that-could-change-the-world-podcast',
            'ext': 'mp3',
            'title': '‘We are just getting started’: the plastic-eating bacteria that could change the world – podcast',
            'description': 'When a microbe was found munching on a plastic bottle in a rubbish dump, it promised a recycling revolution. Now scientists are attempting to turbocharge those powers in a bid to solve our waste crisis. But will it work?',
            'creator': 'Stephen Buranyi',
            'thumbnail': 'md5:73c12558fcb3b0e2a59422bfb33b3f79',
            'release_date': '20231103'
        }
    }, {
        'url': 'https://www.theguardian.com/news/audio/2023/oct/30/the-trials-of-robert-habeck-is-the-worlds-most-powerful-green-politician-doomed-to-fail-podcast',
        'md5': 'd1771744681789b4cd7da2a08e487702',
        'info_dict': {
            'id': 'the-trials-of-robert-habeck-is-the-worlds-most-powerful-green-politician-doomed-to-fail-podcast',
            'ext': 'mp3',
            'title': 'The trials of Robert Habeck: is the world’s most powerful green politician doomed to fail? – podcast',
            'description': 'A year ago, Germany’s vice-chancellor was one of the country’s best-liked public figures. Then came the tabloid-driven backlash. Now he has to win the argument all over again',
            'creator': 'Philip Oltermann',
            'thumbnail': 'md5:6e5c5ec43843e956e20be793722e9080',
            'release_date': '20231030'
        }
    }, {
        'url': 'https://www.theguardian.com/football/audio/2023/nov/06/arsenal-feel-hard-done-by-and-luton-hold-liverpool-football-weekly',
        'md5': 'a2fcff6f8e060a95b1483295273dc35e',
        'info_dict': {
            'id': 'arsenal-feel-hard-done-by-and-luton-hold-liverpool-football-weekly',
            'ext': 'mp3',
            'title': 'Arsenal feel hard done by and Luton hold Liverpool – Football Weekly',
            'description': 'Max Rushden is joined by Barry Glendenning, Jordan Jarrett-Bryan, and Jonathan Wilson to discuss all the weekend’s Premier League action',
            'creator': 'Max Rushden',
            'thumbnail': 'md5:93eb7d6440f1bb94eb3a6cad63f48afd',
            'release_date': '20231106'
        }
    }, {
        'url': 'https://www.theguardian.com/politics/audio/2023/nov/02/the-covid-inquiry-politics-weekly-uk-podcast',
        'md5': '06a0f7e9701a80c8064a5d35690481ec',
        'info_dict': {
            'id': 'the-covid-inquiry-politics-weekly-uk-podcast',
            'ext': 'mp3',
            'title': 'The Covid inquiry | Politics Weekly UK - podcast',
            'description': 'The Guardian’s Gaby Hinsliff talks to political editor Pippa Crerar about what we have learned from the Covid inquiry. And our political correspondent Kiran Stacey tells us how significant the government’s first artificial intelligence summit will be',
            'creator': 'Gaby Hinsliff',
            'thumbnail': 'md5:28932a7b5a25b057be330d2ed70ea7f3',
            'release_date': '20231102'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        return {
            'id': video_id,
            'title': self._og_search_title(webpage) or get_element_by_class('content__headline', webpage),
            'description': self._og_search_description(webpage),
            'creator': self._html_search_meta('author', webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'release_date': unified_strdate(self._html_search_meta('article:published_time', webpage)),
            'url': extract_attributes(get_element_html_by_class('podcast__player', webpage) or '').get('data-source'),
        }
