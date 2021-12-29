# coding: utf-8
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    float_or_none,
    int_or_none
)


class CallinIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?callin\.com/(episode)/(?P<id>[-a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://www.callin.com/episode/the-title-ix-regime-and-the-long-march-through-EBfXYSrsjc',
        'info_dict': {
            'id': '218b979630a35ead12c6fd096f2996c56c37e4d0dc1f6dc0feada32dcf7b31cd',
            'title': 'The Title IX Regime and the Long March Through and Beyond the Institutions',
            'url': 'https://d26nqus0kmgkkk.cloudfront.net/25246512e4b374daea3a23397483c50d241329ff8af4a5bafae02dae06cb0d5f/25246512e4b374daea3a23397483c50d241329ff8af4a5bafae02dae06cb0d5f.m3u8',
            'ext': 'mp3',
            'display_id': 'the-title-ix-regime-and-the-long-march-through-EBfXYSrsjc',
            'thumbnail': 'https://d2xpqol0sc5yi.cloudfront.net/82cf84f4f7b70e3e1f9e36505cce56d97a31d3bd0589156595f362d25e012e06.png',
            'description': 'First episode',
            'uploader': 'Wesley Yang',
            'timestamp': 1639404128.65,
            'upload_date': '20211213',
            'uploader_id': 'wesyang',
            'uploader_url': 'http://wesleyyang.substack.com',
            'channel': 'Conversations in Year Zero',
            'channel_id': '436d1f82ddeb30cd2306ea9156044d8d2cfdc3f1f1552d245117a42173e78553',
            'channel_url': 'https://callin.com/show/conversations-in-year-zero-oJNllRFSfx',
            'duration': 9951.936,
            'view_count': int,
            'categories': ['News & Politics', 'History', 'Technology'],
            'cast': ['Wesley Yang', 'KC Johnson', 'Gabi Abramovich'],
            'series': 'Conversations in Year Zero',
            'series_id': '436d1f82ddeb30cd2306ea9156044d8d2cfdc3f1f1552d245117a42173e78553',
            'episode': 'The Title IX Regime and the Long March Through and Beyond the Institutions',
            'episode_number': 1,
            'episode_id': '218b979630a35ead12c6fd096f2996c56c37e4d0dc1f6dc0feada32dcf7b31cd'
        }
    }]

    def try_get_user_name(self, d):
        names = [d.get(n) for n in ('first', 'last')]
        if None in names:
            return None
        return ' '.join(names)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        next_data = self._search_nextjs_data(webpage, display_id)
        episode = next_data['props']['pageProps']['episode']

        id = episode['id']
        title = episode.get('title')
        url = episode['m3u8']
        formats = self._extract_m3u8_formats(url, id, ext='mp3')
        self._sort_formats(formats)

        show = traverse_obj(episode, ('show', 'title'))
        show_id = traverse_obj(episode, ('show', 'id'))

        # get the show metadata for some supplementary info
        show_json = None
        try:
            app_slug = self._html_search_regex(
                '<script\\s+src=["\']/_next/static/([a-zA-Z0-9_]+)/_',
                webpage, 'app slug', fatal=False)
            if app_slug is None:
                # this sometimes works, but sometimes seems to lag changes in the actual urls used.
                app_slug = next_data['buildId']
            show_slug = episode['show']['linkObj']['resourceUrl'].rsplit('/', 1)[1]
            show_json_url = f'https://www.callin.com/_next/data/{app_slug}/show/{show_slug}.json'

            show_json = self._download_json(show_json_url, id)
        except (KeyError, IndexError, ExtractorError):
            pass

        # if we don't have the show metadata to tell us the host explicitly,
        # guess that it's the first speaker listed for the episode
        host = (traverse_obj(show_json, ('pageProps', 'show', 'hosts', 0))
            or traverse_obj(episode, ('speakers', 0)))

        host_nick = traverse_obj(host, ('linkObj', 'resourceUrl'))
        host_nick = host_nick.rsplit('/', 1)[1] if (host_nick and '/' in host_nick) else None

        cast = list(filter(None, [
            self.try_get_user_name(u) for u in
            traverse_obj(episode, (('speakers', 'callerTags'), ...)) or []
        ]))

        episode_list = traverse_obj(show_json, ('pageProps', 'show', 'episodes')) or []
        episode_number = next(
            (len(episode_list) - i for (i, e) in enumerate(episode_list) if e.get('id') == id),
            None
        )

        return {
            'id': id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'thumbnail': traverse_obj(episode, ('show', 'photo')),
            'description': episode.get('description'),
            'uploader': self.try_get_user_name(host) if host else None,
            'timestamp': episode.get('publishedAt'),
            'uploader_id': host_nick,
            'uploader_url': traverse_obj(show_json, ('pageProps', 'show', 'url')),
            'channel': show,
            'channel_id': show_id,
            'channel_url': traverse_obj(episode, ('show', 'linkObj', 'resourceUrl')),
            'duration': float_or_none(episode.get('runtime')),
            'view_count': int_or_none(episode.get('plays')),
            'categories': traverse_obj(episode, ('show', 'categorizations', ..., 'name')),
            'cast': cast if cast else None,
            'series': show,
            'series_id': show_id,
            'episode': title,
            'episode_number': episode_number,
            'episode_id': id
        }
