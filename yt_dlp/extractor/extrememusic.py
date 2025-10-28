import itertools
import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    join_nonempty,
    merge_dicts,
    str_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class ExtremeMusicBaseIE(InfoExtractor):
    _API_URL = 'https://snapi.extrememusic.com'
    _REQUEST_HEADERS = None
    _REQUIRE_VERSION = []

    def _initialize(self, url, video_id, country=None):
        self._REQUIRE_VERSION = (self._configuration_arg('ver', ie_key='extrememusic')
                                 or self._configuration_arg('version', ie_key='extrememusic'))
        env = self._download_json('https://www.extrememusic.com/env', video_id)
        self._REQUEST_HEADERS = {
            'Accept': 'application/json',
            'Origin': 'https://www.extrememusic.com',
            'Referer': url,
            'Sec-Fetch-Mode': 'cors',
            'X-API-Auth': env['token'],
            'X-Site-Id': 4,
            'X-Viewer-Country': country.upper(),
        }

    def _get_album_data(self, album_id, video_id, fatal=True):
        album = self._download_json(f'{self._API_URL}/albums/{album_id}', video_id, fatal=fatal,
                                    note='Downloading album data', errnote='Unable to download album data',
                                    headers=self._REQUEST_HEADERS) or {}
        if video_id == album_id:
            bio = self._download_json(f'{self._API_URL}/albums/{album_id}/bio', video_id, fatal=False,
                                      note='Downloading album data', errnote='Unable to download album data',
                                      headers=self._REQUEST_HEADERS) or {}
            return merge_dicts(album, bio)
        else:
            return album

    def _extract_track(self, album_data, track_id=None, version_id=None):
        if 'tracks' in album_data and 'track_sounds' in album_data:
            if not track_id and version_id:
                track_id = traverse_obj(album_data, (
                    'track_sounds', lambda _, v: v['id'] == int(version_id), 'track_id', {int}), get_all=False)
            if track := traverse_obj(album_data, (
                    'tracks', lambda _, v: v['id'] == int(track_id), {dict}), get_all=False):
                track_info = {**traverse_obj(track, {
                    'track': ('title', {str}),
                    'track_number': ('sort_order', {lambda v: v + 1}, {int}),
                    'track_id': ('track_no', {str}),
                    'description': ('description', {lambda v: str_or_none(v) or None}),
                    'artists': ('artists', {lambda v: v or traverse_obj(album_data, ('album', 'artist'))},
                                {lambda v: (v if isinstance(v, list) else [v]) if v else None}),
                    'composers': ('composers', ..., 'name'),
                    'genres': (('genre', 'subgenre'), ..., 'label'),
                    'tag': ('keywords', ..., 'label'),
                    'album': ('album_title', {lambda v: str_or_none(v) or None}),
                }), **traverse_obj(album_data, ('album', {
                    'album_artists': ('artist', {lambda v: [v] if v else None}),
                    'upload_date': ('created', {unified_strdate}),
                }))}
                entries, thumbnails = [], []
                for image in traverse_obj(track, ('images', 'default')):
                    thumbnails.append(traverse_obj(image, {
                        'url': ('url', {url_or_none}),
                        'width': ('width', {int_or_none}),
                        'height': ('height', {int_or_none}),
                    }))
                if not self._REQUIRE_VERSION:
                    version_id = (version_id
                                  or traverse_obj(track, 'default_track_sound_id', ('track_sound_ids', 0)))
                for sound_id in [version_id] if version_id else track['track_sound_ids']:
                    if sound := traverse_obj(album_data, (
                            'track_sounds', lambda _, v: v['id'] == int(sound_id) and v['track_id'] == int(track_id),
                            {dict}), get_all=False):
                        if (version_id
                                or 'all' in self._REQUIRE_VERSION
                                or any(x in sound['version_type'].lower() for x in self._REQUIRE_VERSION)):
                            formats = []
                            for audio_url in traverse_obj(
                                    sound, ('assets', 'audio', ('preview_url', 'preview_url_hls'))):
                                if determine_ext(audio_url) == 'm3u8':
                                    m3u8_url = re.sub(r'\.m3u8\?.*', '/HLS/128_v4.m3u8', audio_url)
                                    for f in self._extract_m3u8_formats(m3u8_url, sound_id, 'm4a', fatal=False):
                                        formats.append({
                                            **f,
                                            'vcodec': 'none',
                                            'perference': -2,
                                        })
                                else:
                                    formats.append({
                                        'url': audio_url,
                                        'vcodec': 'none',
                                    })
                            entries.append({
                                'id': str(sound_id),
                                'title': join_nonempty('title', 'version_type', from_dict=sound, delim=' - '),
                                'alt_title': sound['version_type'],
                                **track_info,
                                'thumbnails': thumbnails,
                                'duration': sound.get('duration'),
                                'formats': formats,
                                'webpage_url': f"https://www.extrememusic.com/albums/{track['album_id']}?item={track_id}&ver={sound_id}",
                            })
                return [entries, {
                    'id': track_id,
                    'title': track_info['track'],
                    **track_info,
                }]
        self.raise_no_formats('Track data not found', video_id=track_id)


class ExtremeMusicIE(ExtremeMusicBaseIE):
    _VALID_URL = r'https?://(?:www\.)?extrememusic\.com/albums/(?P<album>\d+)\?(.*item=(?P<id>\d+))?(.*ver=(?P<ver>\d+))?'
    _TESTS = [{
        'url': 'https://www.extrememusic.com/albums/15875?item=263381&ver=1265009&sharedTrack=dHJ1ZQ==',
        'info_dict': {
            'id': '1265009',
            'ext': 'mp3',
            'title': 'FOLLOW - Instrumental',
            'alt_title': 'Instrumental',
            'track': 'FOLLOW',
            'track_number': 5,
            'track_id': 'HPE316_05',
            'artists': ['PRAERS'],
            'composers': ['Joseph Andrew Banfi', 'Thomas Louis James White'],
            'genres': ['POP', 'DREAM', 'INDIE'],
            'tag': 'count:7',
            'album': 'AVALON',
            'album_artists': ['PRAERS'],
            'upload_date': '20240729',
            'thumbnail': 'https://d2oet5a29f64lj.cloudfront.net/img-data/w/2480/album/600/HPE316.jpg',
            'duration': 246,
        },
    }, {
        'url': 'https://www.extrememusic.com/albums/15823?ver=1262087',
        'info_dict': {
            'id': '1262087',
            'ext': 'mp3',
            'title': 'MAGICAL HIGHWAY - VOCALS',
            'alt_title': 'VOCALS',
            'track': 'MAGICAL HIGHWAY',
            'track_number': 2,
            'track_id': 'ASM0002_02',
            'description': 'Full version - a fun, happy and upbeat pop track with a medium - fast tempo - electronic, bouncy, bright',
            'composers': ['ENB'],
            'genres': ['POP', 'ELECTRO', 'JPOP'],
            'tag': 'count:8',
            'album': 'TOKYO POPPIN\'',
            'upload_date': '20240709',
            'thumbnail': 'https://d2oet5a29f64lj.cloudfront.net/img-data/w/2480/album/600/ASM0002.jpg',
            'duration': 265,
        },
    }, {
        'url': 'https://www.extrememusic.com/albums/15064?item=254704',
        'info_dict': {
            'id': '1178851',
            'ext': 'mp3',
            'title': 'SWEET TOOTH - Full Version',
            'alt_title': 'Full Version',
            'track': 'SWEET TOOTH',
            'track_number': 2,
            'track_id': 'HPE263_02',
            'artists': ['PILOT PAISLEY-ROSE'],
            'composers': ['PILOT PAISLEY ROSE SARACENO', 'SAMUEL JAMES BRANDT'],
            'genres': ['POP', 'ELECTRO', 'ROCK'],
            'tag': 'count:7',
            'album': 'ADDICTED',
            'album_artists': ['PILOT PAISLEY-ROSE'],
            'upload_date': '20230629',
            'thumbnail': 'https://d2oet5a29f64lj.cloudfront.net/img-data/w/2480/album/600/HPE263.jpg',
            'duration': 161,
        },
    }, {
        'url': 'https://www.extrememusic.com/albums/1315?item=24795',
        'info_dict': {
            'id': '61003',
            'ext': 'mp3',
            'title': 'JOY TO THE WORLD (INST) - Instrumental',
            'alt_title': 'Instrumental',
            'track': 'JOY TO THE WORLD (INST)',
            'track_number': 6,
            'track_id': 'XEL016_06',
            'composers': ['TRADITIONAL'],
            'genres': ['HOLIDAY', 'CHRISTMAS'],
            'tag': 'count:5',
            'album': 'CHRISTMAS SPARKLE',
            'upload_date': '20041001',
            'thumbnail': 'https://d2oet5a29f64lj.cloudfront.net/img-data/w/2480/album/600/XEL016.jpg',
            'duration': 132,
        },
    }]

    def _real_extract(self, url):
        album_id, track_id, version_id = self._match_valid_url(url).group('album', 'id', 'ver')
        self._initialize(url, version_id or track_id, self.get_param('geo_bypass_country') or 'DE')
        album_data = self._get_album_data(album_id, version_id or track_id)
        if track := self._extract_track(album_data, track_id, version_id):
            if len(track[0]) > 1:
                return self.playlist_result(track[0], **track[1])
            elif len(track[0]) == 1:
                return track[0][0]
        self.raise_no_formats('No formats were found')


class ExtremeMusicAIE(ExtremeMusicBaseIE):
    IE_NAME = 'ExtremeMusic:album'
    _VALID_URL = r'https?://(?:www\.)?extrememusic\.com/albums/(?P<id>\d+)(?!.*(item|ver)=)'
    _TESTS = [{
        'url': 'https://www.extrememusic.com/albums/6778',
        'info_dict': {
            'id': '6778',
            'album': 'Ethereal Voices',
        },
        'playlist_count': 11,
    }, {
        'url': 'https://www.extrememusic.com/albums/15835',
        'info_dict': {
            'id': '15835',
            'album': 'BIGGEST BANG',
            'description': 'Minus Aura, a minimalist duo who create deep drama and emotion to put you under their spell.',
            'artists': ['MINUS AURA'],
            'genres': ['ELECTRONICA', 'POP', 'SYNTH'],
            'tag': ['ELECTRONIC', 'STRUGGLE'],
        },
        'playlist_count': 4,
    }]

    def _real_extract(self, url):
        album_id = self._match_id(url)
        self._initialize(url, album_id, self.get_param('geo_bypass_country') or 'DE')
        album_data = self._get_album_data(album_id, album_id)
        subgenres = traverse_obj(album_data, ('album', 'subgenres', {str_or_none}))
        album_info = merge_dicts(traverse_obj(album_data, ('album', {
            'id': ('id', {lambda v: str(v)}),
            'album': ('title', {str_or_none}),
            'description': ('description', {lambda v: str_or_none(v) or None}),
            'artists': ('artist', {lambda v: [v] if v else None}),
            'genres': ('genres', {str_or_none},
                       {lambda v: join_nonempty(v, subgenres, delim=', ')},
                       {lambda v: v.split(', ') if v else None}),
            'tag': ('keywords', {lambda v: v.split(', ') if v else None}),
        })), {
            'description': traverse_obj(
                album_data, ('bio', 'description', {lambda v: str_or_none(v) or None})),
        })

        return self.playlist_result(
            (entry for sounds in (track[0] for track in (self._extract_track(album_data, track_id=track_id)
                                                         for track_id in traverse_obj(album_data, ('tracks', ..., 'id'))))
             for entry in sounds),
            **album_info)


class ExtremeMusicPIE(ExtremeMusicBaseIE):
    IE_NAME = 'ExtremeMusic:playlist'
    _VALID_URL = r'https?://(?:www\.)?extrememusic\.com/playlists/(?P<id>[^?]+)'
    _TESTS = [{
        'url': 'https://www.extrememusic.com/playlists/Kf3fAppAKK2UpAUUp7KK1pBDBMrC62c_Kf8UKAAppUUKppK2UAp92K7Appp8xMx',
        'info_dict': {
            'id': 'Kf3fAppAKK2UpAUUp7KK1pBDBMrC62c_Kf8UKAAppUUKppK2UAp92K7Appp8xMx',
            'title': 'NICE',
            'thumbnail': 'https://d2oet5a29f64lj.cloudfront.net/img-data/w/2480/featureditem/square/thumbnail_PLAYLIST_Nice-square-(formerly ChristmasTraditional).jpg',
        },
        'playlist_count': 40,
    }, {
        'url': 'https://www.extrememusic.com/playlists/fUKKU5KAfK61pAAKp4U4KpKUxsRk2ki_fU117KpUUAAUKAUfpA6UAfAKK8Ul5ji',
        'info_dict': {
            'id': 'fUKKU5KAfK61pAAKp4U4KpKUxsRk2ki_fU117KpUUAAUKAUfpA6UAfAKK8Ul5ji',
            'title': 'NEO CLASSICAL',
            'thumbnail': 'https://d2oet5a29f64lj.cloudfront.net/img-data/w/2480/featureditem/square/NeoClassical.jpg',
        },
        'playlist_mincount': 50,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        self._initialize(url, playlist_id, self.get_param('geo_bypass_country') or 'DE')

        def playlist_query(playlist_id, offset, limit, note=None):
            # playlist api: https://snapi.extrememusic.com/playlists?id={playlist_id}&range={offset}%2C{limit}'
            return self._download_json(
                f'{self._API_URL}/playlists', playlist_id, note=note, query={
                    'id': playlist_id,
                    'range': f'{offset + 1},{limit}',
                }, headers=self._REQUEST_HEADERS)

        def extract_playlist(playlist_id):
            albums, tracks_done, items_count, limit = {}, [], 0, 25
            for i in itertools.count():
                try:
                    # try to tackle geo restriction by shortening playlist id
                    playlist = playlist_query(playlist_id.split('_')[0], i * limit, limit,
                                              note=f'Downloading item {i * limit + 1}-{i * limit + limit}')
                except Exception:
                    playlist = playlist_query(playlist_id, i * limit, limit,
                                              note=f'Downloading item {i * limit + 1}-{i * limit + limit}')
                if playlist_items_count := traverse_obj(playlist, ('playlist', 'playlist_items_count')):
                    if len(playlist.get('tracks', [])) == 0:
                        if items_count < playlist_items_count:
                            self.report_warning('This playlist has geo-restricted items. Try using --xff to specify a different country code')
                        break
                    else:
                        track_ids = traverse_obj(playlist, ('tracks', ..., 'id'))
                        items_count += len(track_ids)
                        for track_id in list(dict.fromkeys(track_ids)):
                            if track_id not in tracks_done:
                                album_id = traverse_obj(
                                    playlist, ('tracks', lambda _, v: v['id'] == track_id,
                                               'album_id', {int}), get_all=False)
                                if album_id not in albums:
                                    albums[album_id] = self._get_album_data(album_id, track_id, fatal=False)
                                playlist['album'] = traverse_obj(albums, (album_id, 'album', {dict}))
                                if track := self._extract_track(playlist, track_id=track_id):
                                    if len(track[0]) > 1:
                                        yield from track[0]
                                    elif len(track[0]) == 1:
                                        yield track[0][0]
                                tracks_done.append(track_id)
                    if items_count >= playlist_items_count:
                        break
                else:
                    return []

        playlist_info, thumbnails = {}, []
        if playlist := playlist_query(playlist_id, 0, 1, note='Downloading JSON metadata'):
            for image in traverse_obj(playlist, ('playlist', 'images', 'square')):
                thumbnails.append(traverse_obj(image, {
                    'url': ('url', {url_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                }))
            playlist_info = {
                **traverse_obj(playlist, ('playlist', {
                    'id': ('id', {str}),
                    'title': ('title', {str_or_none}),
                    'uploader': ('owner_name', {str_or_none}),
                })),
                'thumbnail': traverse_obj(thumbnails, (0, 'url', {url_or_none})),
                'thumbnails': thumbnails,
            }
        return self.playlist_result(extract_playlist(playlist_id), **playlist_info)
