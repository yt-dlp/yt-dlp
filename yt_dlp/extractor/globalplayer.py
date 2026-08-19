from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    urlhandle_detect_ext,
)


class GlobalPlayerBaseIE(InfoExtractor):
    def _get_page_props(self, url, video_id):
        webpage = self._download_webpage(url, video_id)
        return self._search_nextjs_data(webpage, video_id)['props']['pageProps']

    def _request_ext(self, url, video_id):
        # Server rejects HEAD requests
        return urlhandle_detect_ext(self._request_webpage(url, video_id))


class GlobalPlayerLiveIE(GlobalPlayerBaseIE):
    _VALID_URL = r'https?://www\.globalplayer\.com/live/(?P<id>\w+)/\w+'
    _TESTS = [{
        'url': 'https://www.globalplayer.com/live/smoothchill/uk/',
        'info_dict': {
            'id': '2mx1E',
            'ext': 'aac',
            'live_status': 'is_live',
            'thumbnail': 'md5:d5040f26c7c4061014a44866129b900e',
            'description': 'Music To Chill To',
            'title': 're:^Smooth Chill.+$',
        },
    }, {
        # national station
        'url': 'https://www.globalplayer.com/live/heart/uk/',
        'info_dict': {
            'id': '2mwx4',
            'ext': 'aac',
            'live_status': 'is_live',
            'description': 'Turn Up the Feel Good!',
            'thumbnail': 'md5:6f13378a53ce55bcf57365a654e1b490',
            'title': 're:^Heart UK.+$',
        },
    }, {
        # regional variation
        'url': 'https://www.globalplayer.com/live/heart/london/',
        'info_dict': {
            'id': 'AMqg',
            'ext': 'aac',
            'live_status': 'is_live',
            'description': 'Turn Up the Feel Good!',
            'thumbnail': 'md5:6f13378a53ce55bcf57365a654e1b490',
            'title': 're:^Heart London.+$',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        meta = self._get_page_props(url, video_id)['station']
        stream_url = meta['streamUrl']

        return {
            'url': stream_url,
            'is_live': True,
            'ext': self._request_ext(stream_url, video_id),
            **traverse_obj(meta, {
                'id': ('id', {str}, {require('video ID')}),
                'thumbnail': ('brandLogo', {url_or_none}),
                'description': ('tagline', {str}),
                'title': ('name', {str}),
            }),
        }


class GlobalPlayerLivePlaylistIE(GlobalPlayerBaseIE):
    _VALID_URL = r'https?://www\.globalplayer\.com/playlists/(?P<id>\w+)'
    _TESTS = [{
        # live playlist
        'url': 'https://www.globalplayer.com/playlists/8bLk/',
        'info_dict': {
            'id': '8bLk',
            'ext': 'aac',
            'live_status': 'is_live',
            'thumbnail': 'md5:391a13cc087b42f626e9e65bbeaf0a11',
            'description': 'md5:f015f2f6c6f6a807669ebcc9a0ca147c',
            'title': 're:^Classic FM Hall of Fame.+$',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        meta = self._get_page_props(url, video_id)['playlistData']
        stream_url = meta['streamUrl']

        return {
            'url': stream_url,
            'id': video_id,
            'is_live': True,
            'ext': self._request_ext(stream_url, video_id),
            **traverse_obj(meta, {
                'thumbnail': ('image', {url_or_none}),
                'description': ('description', {str}),
                'title': ('title', {str}),
            }),
        }


class GlobalPlayerAudioIE(GlobalPlayerBaseIE):
    _VALID_URL = r'https?://www\.globalplayer\.com/(?:(?P<podcast>podcasts)/|catchup/\w+/\w+/)(?P<id>\w+)/?(?:$|[?#])'
    _TESTS = [{
        # podcast
        'url': 'https://www.globalplayer.com/podcasts/42KuaM/',
        'playlist_mincount': 5,
        'info_dict': {
            'id': '42KuaM',
            'thumbnail': 'md5:60286e7d12d795bd1bbc9efc6cee643e',
            'description': 'md5:17b7b9e3c76b2f4d9e31ccc4f0b66e32',
            'title': 'Filthy Ritual',
        },
    }, {
        # radio catchup
        'url': 'https://www.globalplayer.com/catchup/lbc/uk/46vyD7z/',
        'playlist_mincount': 3,
        'info_dict': {
            'id': '46vyD7z',
            'thumbnail': 'md5:664ad62a8fb920a2b8e264ed780eee3d',
            'description': 'Nick Ferrari At Breakfast is Leading Britain\'s Conversation.',
            'title': 'Nick Ferrari',
        },
    }]

    def _real_extract(self, url):
        video_id, podcast = self._match_valid_url(url).group('id', 'podcast')
        props = self._get_page_props(url, video_id)
        if podcast:
            meta = props['podcastInfo']['metadata']
            blocks = props['podcastInfo']['blocks'][1]['items']
        else:
            meta = props['catchupInfo']['metadata']
            blocks = props['catchupInfo']['blocks'][1]['items']

        def _entries():
            for block in blocks:
                entry_id = block['id']
                data = self._download_json(
                    f'https://bff-web-guacamole.musicradio.com/playables/{entry_id}',
                    video_id, f'Downloading metadata JSON for {entry_id}')
                yield {
                    'id': entry_id,
                    'url': traverse_obj(data, ('playback', 0, 'url')),
                    **traverse_obj(block, {
                        'thumbnail': ('image', 'url', {url_or_none}),
                        'description': ('description', {str}),
                        'title': ('title', {str}),
                    }),
                }

        return {
            '_type': 'playlist',
            'id': video_id,
            'entries': _entries(),
            **traverse_obj(meta, {
                'thumbnail': ('image', 'url', {url_or_none}),
                'description': ('description', {str}),
                'title': ('title', {str}),
            }),
        }


class GlobalPlayerAudioEpisodeIE(GlobalPlayerBaseIE):
    _VALID_URL = r'https?://www\.globalplayer\.com/(?:(?P<podcast>podcasts)|catchup/\w+/\w+)/episodes/(?P<id>\w+)/?(?:$|[?#])'
    _TESTS = [{
        # podcast
        'url': 'https://www.globalplayer.com/podcasts/episodes/7DrorSc/',
        'info_dict': {
            'id': '7DrorSc',
            'ext': 'mp3',
            'thumbnail': 'md5:60286e7d12d795bd1bbc9efc6cee643e',
            'description': 'md5:372e5aa2b531f9eba863dfc67d007c1c',
            'title': 'Filthy Ritual - Trailer',
        },
    }, {
        # radio catchup - test urls are removed after 7 days
        'url': 'https://www.globalplayer.com/catchup/lbc/uk/episodes/2zGt5k1jDPUA13dZtsKZ6vrsHX/',
        'info_dict': {
            'id': '2zGt5k1jDPUA13dZtsKZ6vrsHX',
            'ext': 'm4a',
            'thumbnail': 'md5:664ad62a8fb920a2b8e264ed780eee3d',
            'description': 'Nick Ferrari At Breakfast is Leading Britain\'s Conversation.',
            'title': 'Nick Ferrari',
        },
    }]

    def _real_extract(self, url):
        video_id, podcast = self._match_valid_url(url).group('id', 'podcast')
        props = self._get_page_props(url, video_id)
        meta = props['podcastEpisode']['metadata'] if podcast else props['catchupEpisode']['metadata']
        data = self._download_json(f'https://bff-web-guacamole.musicradio.com/playables/{video_id}', video_id)

        return {
            'id': video_id,
            **traverse_obj(data, {
                'url': ('playback', 0, 'url', {url_or_none}),
            }),
            **traverse_obj(meta, {
                'thumbnail': ('image', 'url', {url_or_none}),
                'description': ('description', {str}),
                'title': ('title', {str}),
            }),
        }


class GlobalPlayerVideoIE(GlobalPlayerBaseIE):
    _VALID_URL = r'https?://www\.globalplayer\.com/videos/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.globalplayer.com/videos/2JsSZ7Gm2uP/',
        'info_dict': {
            'id': '2JsSZ7Gm2uP',
            'ext': 'mp4',
            'thumbnail': 'md5:d4498af48e15aae4839ce77b97d39550',
            'description': 'md5:6a9f063c67c42f218e42eee7d0298bfd',
            'title': 'Treble Malakai Bayoh sings a sublime Handel aria at Classic FM Live',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        meta = self._get_page_props(url, video_id)['videoData']

        return {
            'id': video_id,
            **traverse_obj(meta, {
                'url': ('url', {url_or_none}),
                'thumbnail': ('image', 'url', {url_or_none}),
                'description': ('description', {str}),
                'title': ('title', {str}),
            }),
        }
