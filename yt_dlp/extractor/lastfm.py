import itertools
import re

from .common import InfoExtractor
from ..utils import int_or_none, parse_qs, traverse_obj


class LastFMPlaylistBaseIE(InfoExtractor):
    def _entries(self, url, playlist_id):
        single_page = traverse_obj(parse_qs(url), ('page', -1, {int_or_none}))
        for page in itertools.count(single_page or 1):
            webpage = self._download_webpage(
                url, playlist_id, f'Downloading page {page}', query={'page': page})
            videos = re.findall(r'data-youtube-url="([^"]+)"', webpage)
            yield from videos
            if single_page or not videos:
                return

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        return self.playlist_from_matches(self._entries(url, playlist_id), playlist_id, ie='Youtube')


class LastFMPlaylistIE(LastFMPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?last\.fm/(music|tag)/(?P<id>[^/]+)(?:/[^/]+)?/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.last.fm/music/Oasis/(What%27s+the+Story)+Morning+Glory%3F',
        'info_dict': {
            'id': 'Oasis',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'https://www.last.fm/music/Oasis',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis/',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis?top_tracks_date_preset=ALL#top-tracks',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis/+tracks',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis/+tracks?page=2',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Oasis/+tracks?date_preset=LAST_90_DAYS#top-tracks',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/tag/rock',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/tag/rock/tracks',
        'only_matching': True,
    }]


class LastFMUserIE(LastFMPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?last\.fm/user/[^/]+/playlists/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://www.last.fm/user/mehq/playlists/12319471',
        'info_dict': {
            'id': '12319471',
        },
        'playlist_count': 30,
    }, {
        'url': 'https://www.last.fm/user/naamloos1/playlists/12543760',
        'info_dict': {
            'id': '12543760',
        },
        'playlist_mincount': 80,
    }, {
        'url': 'https://www.last.fm/user/naamloos1/playlists/12543760?page=3',
        'info_dict': {
            'id': '12543760',
        },
        'playlist_count': 32,
    }]


class LastFMIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?last\.fm/music(?:/[^/]+){2}/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://www.last.fm/music/Oasis/_/Wonderwall',
        'md5': '9c4a70c2e84c03d54fe24229b9e13b7b',
        'info_dict': {
            'id': '6hzrDeceEKc',
            'ext': 'mp4',
            'title': 'Oasis - Wonderwall  (Official Video)',
            'thumbnail': r're:^https?://i.ytimg.com/.*\.jpg$',
            'description': 'md5:0848669853c10687cc28e88b5756738f',
            'uploader': 'Oasis',
            'uploader_id': 'oasisinetofficial',
            'upload_date': '20080207',
            'album': '(What\'s The Story) Morning Glory? (Remastered)',
            'track': 'Wonderwall (Remastered)',
            'channel_id': 'UCUDVBtnOQi4c7E8jebpjc9Q',
            'view_count': int,
            'live_status': 'not_live',
            'channel_url': 'https://www.youtube.com/channel/UCUDVBtnOQi4c7E8jebpjc9Q',
            'tags': 'count:39',
            'creator': 'Oasis',
            'uploader_url': 're:^https?://www.youtube.com/user/oasisinetofficial',
            'duration': 279,
            'alt_title': 'Wonderwall (Remastered)',
            'age_limit': 0,
            'channel': 'Oasis',
            'channel_follower_count': int,
            'categories': ['Music'],
            'availability': 'public',
            'like_count': int,
            'playable_in_embed': True,
            'artist': 'Oasis',
        },
        'add_ie': ['Youtube'],
    }, {
        'url': 'https://www.last.fm/music/Oasis/_/Don%27t+Look+Back+In+Anger+-+Remastered/',
        'only_matching': True,
    }, {
        'url': 'https://www.last.fm/music/Guns+N%27+Roses/_/Sweet+Child+o%27+Mine',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player_url = self._search_regex(r'(?s)class="header-new-playlink"\s+href="([^"]+)"', webpage, 'player_url')

        track_or_album = re.search(r'(?s)class="header-new-playlink".*?(Play\s+(?:track|album))', webpage).group(1)
        media_type = None
        if track_or_album == 'Play track':
            media_type = 'track'
        elif track_or_album == 'Play album':
            media_type = 'album'

        def get_albums(webpage):
            base_url = 'https://www.last.fm'
            albums = re.findall(r'(?s)class="source-album-details".*?href="([^"]+)"', webpage)
            return list(set([base_url + url if url.startswith('/') else url for url in albums]))

        def get_album_meta(webpage):
            thumbnail = re.search(r'(?s)class="cover-art".*?img\s+src="([^"]+)"', webpage).group(1)
            release_date = re.search(r'(?s)class="catalogue-metadata-heading">Release\s+Date</dt>.*?>(\d+)\s+(\w+)\s+(\d+)</dd>', webpage).groups()
            import datetime
            release_date = datetime.datetime.strptime(' '.join(release_date), '%d %B %Y').date()
            return {'thumbnail': thumbnail, 'release_date': release_date}

        if media_type == 'track':
            albums = get_albums(webpage)
            albums_meta = []
            import urllib.request as req
            for album in albums:
                with req.urlopen(album) as response:
                    album_webpage = response.read().decode('utf-8')
                album_meta = get_album_meta(album_webpage)
                albums_meta.append(album_meta)
            earliest_album = sorted(albums_meta, key=lambda a: a['release_date'])[0]
            thumbnail = earliest_album['thumbnail']

        result = self.url_result(player_url, 'Youtube')
        thumbnails = [{'url': thumbnail}]
        result['thumbnails'] = thumbnails
        result['_type'] = 'url_transparent'
        return result
