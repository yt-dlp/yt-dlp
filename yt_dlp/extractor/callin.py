from .common import InfoExtractor
from ..utils import float_or_none, int_or_none, make_archive_id, traverse_obj


class CallinIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?callin\.com/episode/(?P<id>[-a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://www.callin.com/episode/the-title-ix-regime-and-the-long-march-through-EBfXYSrsjc',
        'info_dict': {
            'id': '218b979630a35ead12c6fd096f2996c56c37e4d0dc1f6dc0feada32dcf7b31cd',
            'title': 'The Title IX Regime and the Long March Through and Beyond the Institutions',
            'ext': 'ts',
            'display_id': 'the-title-ix-regime-and-the-long-march-through-EBfXYSrsjc',
            'thumbnail': 're:https://.+\\.png',
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
            'episode_id': '218b979630a35ead12c6fd096f2996c56c37e4d0dc1f6dc0feada32dcf7b31cd',
        },
    }, {
        'url': 'https://www.callin.com/episode/fcc-commissioner-brendan-carr-on-elons-PrumRdSQJW',
        'md5': '14ede27ee2c957b7e4db93140fc0745c',
        'info_dict': {
            'id': 'c3dab47f237bf953d180d3f243477a84302798be0e0b29bc9ade6d60a69f04f5',
            'ext': 'ts',
            'title': 'FCC Commissioner Brendan Carr on Elon’s Starlink',
            'description': 'Or, why the government doesn’t like SpaceX',
            'channel': 'The Pull Request',
            'channel_url': 'https://callin.com/show/the-pull-request-ucnDJmEKAa',
            'duration': 3182.472,
            'series_id': '7e9c23156e4aecfdcaef46bfb2ed7ca268509622ec006c0f0f25d90e34496638',
            'uploader_url': 'http://thepullrequest.com',
            'upload_date': '20220902',
            'episode': 'FCC Commissioner Brendan Carr on Elon’s Starlink',
            'display_id': 'fcc-commissioner-brendan-carr-on-elons-PrumRdSQJW',
            'series': 'The Pull Request',
            'channel_id': '7e9c23156e4aecfdcaef46bfb2ed7ca268509622ec006c0f0f25d90e34496638',
            'view_count': int,
            'uploader': 'Antonio García Martínez',
            'thumbnail': 'https://d1z76fhpoqkd01.cloudfront.net/shows/legacy/1ade9142625344045dc17cf523469ced1d93610762f4c886d06aa190a2f979e8.png',
            'episode_id': 'c3dab47f237bf953d180d3f243477a84302798be0e0b29bc9ade6d60a69f04f5',
            'timestamp': 1662100688.005,
        },
    }, {
        'url': 'https://www.callin.com/episode/episode-81-elites-melt-down-over-student-debt-lzxMidUnjA',
        'md5': '16f704ddbf82a27e3930533b12062f07',
        'info_dict': {
            'id': '8d06f869798f93a7814e380bceabea72d501417e620180416ff6bd510596e83c',
            'ext': 'ts',
            'title': 'Episode 81- Elites MELT DOWN over Student Debt Victory? Rumble in NYC?',
            'description': 'Let’s talk todays episode about the primary election shake up in NYC and the elites melting down over student debt cancelation.',
            'channel': 'The DEBRIEF With Briahna Joy Gray',
            'channel_url': 'https://callin.com/show/the-debrief-with-briahna-joy-gray-siiFDzGegm',
            'duration': 10043.16,
            'series_id': '61cea58444465fd26674069703bd8322993bc9e5b4f1a6d0872690554a046ff7',
            'uploader_url': 'http://patreon.com/badfaithpodcast',
            'upload_date': '20220826',
            'episode': 'Episode 81- Elites MELT DOWN over Student Debt Victory? Rumble in NYC?',
            'display_id': 'episode-',
            'series': 'The DEBRIEF With Briahna Joy Gray',
            'channel_id': '61cea58444465fd26674069703bd8322993bc9e5b4f1a6d0872690554a046ff7',
            'view_count': int,
            'uploader': 'Briahna Gray',
            'thumbnail': 'https://d1z76fhpoqkd01.cloudfront.net/shows/legacy/461ea0d86172cb6aff7d6c80fd49259cf5e64bdf737a4650f8bc24cf392ca218.png',
            'episode_id': '8d06f869798f93a7814e380bceabea72d501417e620180416ff6bd510596e83c',
            'timestamp': 1661476708.282,
        },
    }]

    def try_get_user_name(self, d):
        names = [d.get(n) for n in ('first', 'last')]
        if None in names:
            return next((n for n in names if n), default=None)
        return ' '.join(names)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        next_data = self._search_nextjs_data(webpage, display_id)
        episode = next_data['props']['pageProps']['episode']

        video_id = episode['id']
        title = episode.get('title') or self._generic_title('', webpage)
        url = episode['m3u8']
        formats = self._extract_m3u8_formats(url, display_id, ext='ts')

        show = traverse_obj(episode, ('show', 'title'))
        show_id = traverse_obj(episode, ('show', 'id'))

        show_json = None
        app_slug = (self._html_search_regex(
            '<script\\s+src=["\']/_next/static/([-_a-zA-Z0-9]+)/_',
            webpage, 'app slug', fatal=False) or next_data.get('buildId'))
        show_slug = traverse_obj(episode, ('show', 'linkObj', 'resourceUrl'))
        if app_slug and show_slug and '/' in show_slug:
            show_slug = show_slug.rsplit('/', 1)[1]
            show_json_url = f'https://www.callin.com/_next/data/{app_slug}/show/{show_slug}.json'
            show_json = self._download_json(show_json_url, display_id, fatal=False)

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
            (len(episode_list) - i for i, e in enumerate(episode_list) if e.get('id') == video_id),
            None)

        return {
            'id': video_id,
            '_old_archive_ids': [make_archive_id(self, display_id.rsplit('-', 1)[-1])],
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
            'episode_id': video_id,
        }
