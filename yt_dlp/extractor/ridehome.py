from .common import InfoExtractor

from ..utils import (
    clean_html,
    determine_ext,
    extract_attributes,
    float_or_none,
    get_element_by_class,
    get_element_html_by_class,
    int_or_none,
    mimetype2ext,
    traverse_obj
)


class RideHomeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ridehome\.info/show/techmeme-ride-home/(?P<id>[\w-]+)(?:/|$)'
    _TESTS = [{
        'url': 'https://www.ridehome.info/show/techmeme-ride-home/thu-1228-will-2024-be-the-year-apple-gets-serious-about-gaming-on-macs/',
        'md5': 'c84ea3cc96950a9ab86fe540f3edc588',
        'info_dict': {
            'id': '540e5493-9fe6-4c14-a488-dc508d8794b2',
            'ext': 'mp3',
            'title': 'Thu. 12/28 – Will 2024 Be The Year Apple Gets Serious About Gaming On Macs?',
            'description': 'md5:a5fa37bfebfc5bd7aaea01b19d59ab3b',
            'series': 'Techmeme Ride Home',
            'duration': 1000.1502,
            'thumbnail': r're:^https?://content\.production\.cdn\.art19\.com/images/.*\.jpeg$'
        }
    }, {
        'url': 'https://www.ridehome.info/show/techmeme-ride-home/portfolio-profile-sensel-with-ilyarosenberg/',
        'md5': 'bf9d6efad221008ce71aea09d5533cf6',
        'info_dict': {
            'id': '6beed803-b1ef-4536-9fef-c23cf6b4dcac',
            'ext': 'mp3',
            'title': '(Portfolio Profile) Sensel - With @IlyaRosenberg',
            'description': 'md5:4724c828b0eea666aad8bdcbdfe8fed3',
            'series': 'Techmeme Ride Home',
            'duration': 2789.38122,
            'thumbnail': r're:^https?://content\.production\.cdn\.art19\.com/images/.*\.jpeg$'
        }
    }]

    _HEADERS = {
        'Accept': 'application/json',
        'Origin': 'https://www.art19.com',
        'Referer': 'https://www.art19.com/'
    }

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)

        episode_id = self._html_search_regex(
            r'https://www.art19.com/shows/techmeme-ridehome/episodes/(.+?)/embed', extract_attributes(
                get_element_html_by_class('iframeContainer', webpage) or '').get('data-src'), 'Episode id')

        description = clean_html(get_element_by_class('lead', webpage) or '') or self._og_search_description(webpage)

        media_json = self._download_json(
            f'https://rss.art19.com/external/episodes/{episode_id}', article_id,
            note=f'Download information for episode with id {episode_id}', headers=self._HEADERS)

        media = traverse_obj(media_json, {
            'title': ('content', 'episode_title'),
            'duration': ('content', 'duration', {float_or_none}),
            'media': ('content', 'media', ...),
            'thumbs': ('content', 'artwork', 'episode'),
            'series': ('content', 'series_title'),
        })

        formats = []
        for track in media.get('media'):
            ext = mimetype2ext(track.get('content_type')) or determine_ext(track.get('url'))
            formats.append({
                'url': track.get('url'),
                'ext': ext
            })
        thumbnails = []
        for thumb in media.get('thumbs'):
            thumbnails.append({
                'url': thumb.get('url'),
                'width': int_or_none(thumb.get('width')),
                'height': int_or_none(thumb.get('height')),
            })

        return {
            'id': episode_id,
            'title': self._og_search_title(webpage) or media.get('title'),
            'description': description,
            'series': media.get('series'),
            'duration': media.get('duration'),
            'formats': formats,
            'thumbnails': thumbnails
        }
