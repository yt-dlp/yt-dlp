import json
import re
from hashlib import md5
from .common import InfoExtractor
from ..utils import (
    str_to_int,
    traverse_obj,
)


class DeezerBaseInfoExtractor(InfoExtractor):

    GW_LIGHT_URL = "https://www.deezer.com/ajax/gw-light.php"
    GET_URL = "https://media.deezer.com/v1/get_url"
    EXPLORE_URL = "https://www.deezer.com/en/channels/explore"

    def get_key_dynamically(self):
        explore_webpage = self._download_webpage(self.EXPLORE_URL, 1)
        app_url = self._html_search_regex(r'(?<=script src=\")(https:\/\/[a-z-\.\/]+app-web[a-z0-9\.]+)', explore_webpage, 'explore_webpage')

        app_webpage = self._download_webpage(app_url, 1)

        t1 = self._html_search_regex(r'(%5B0x61(%2C0x[0-9a-z+]+)+%2C0x67%5D)', app_webpage, 'app_webpage')
        t1 = t1.replace("%5B", "").replace("%2C", "").replace("%5D", "").replace("%5B", "").replace("0x", "")
        t1 = bytes.fromhex(t1).decode('utf-8')

        t2 = self._html_search_regex(r'(%5B0x31(%2C0x[0-9a-z+]+)+%2C0x34%5D)', app_webpage, 'app_webpage')
        t2 = t2.replace("%5B", "").replace("%2C", "").replace("%5D", "").replace("%5B", "").replace("0x", "")
        t2 = bytes.fromhex(t2).decode('utf-8')

        if (len(t1) != 8 or len(t2) != 8):
            raise Exception("Dynamic key is incorrect")

        key = ""
        for i in range(1, 9):
            key += t1[-i] + t2[-i]

        self.blowfish_key = key.encode('utf-8')

    def compute_blowfish_key(self, songid):

        h = md5(str(songid).encode('ascii')).hexdigest().encode('utf-8')
        return "".join(chr(h[i] ^ h[i + 16] ^ self.blowfish_key[i]) for i in range(16))

    def get_data(self, url):

        mobj = re.match(self._VALID_URL, url)
        data_id = mobj.group('id')
        country = mobj.group('country')
        url = self._API_URL.format(data_id)
        response = self._download_json(url, data_id)
        return data_id, country, response

    def get_api_license_tokens(self, data_id):

        url = self.GW_LIGHT_URL + "?" + \
            "api_token=&" + \
            "method=deezer.getUserData&" + \
            "input=3&" + \
            "api_version=1.0&" + \
            "cid=550330597"

        response = self._download_json(url, data_id)
        api_token = traverse_obj(response, ('results', 'checkForm'))
        license_token = traverse_obj(response, ('results', 'USER', 'OPTIONS', 'license_token'))

        return api_token, license_token


class DeezerMusicExtractor(DeezerBaseInfoExtractor):

    def get_entries(self, data_id, data, json_data):

        #################################
        # GET API TOKEN & LICENSE TOKEN #
        #################################

        api_token, license_token = self.get_api_license_tokens(data_id)

        #####################
        # GET DIRECT STREAM #
        #####################

        url = self.GW_LIGHT_URL + "?" + \
            "api_token=" + api_token + "&" + \
            "method=" + self._METHOD + "&" + \
            "input=3&" + \
            "api_version=1.0&" + \
            "cid=550330597"

        response = self._download_json(url, data_id, data=json.dumps(json_data).encode('utf-8'))

        entries = []
        for track in traverse_obj(response, ('results', 'data')):

            entries.append({
                'id': track.get('SNG_ID'),
                'duration': str_to_int(track.get('DURATION')),
                'title': track.get('SNG_TITLE'),
                'uploader': track.get('ART_NAME'),
                'artist': track.get('ART_NAME'),
                'uploader_id': track.get('ART_ID'),
                'track_number': str_to_int(track.get('TRACK_NUMBER')),
                'release_date': str_to_int(track.get('DIGITAL_RELEASE_DATE', '').replace(' ', '')),
                'album': track.get('ALB_TITLE'),
                'formats': [{
                    'format_id': 'MP3_PREVIEW',
                    'url': track.get('MEDIA', [{}])[0].get('HREF'),
                    'preference': -3,
                    'ext': 'mp3',
                    'track_token': track.get('TRACK_TOKEN'),
                }]
            })

        ###############
        # GET FORMATS #
        ###############

        track_tokens = [entry.get('formats', [{}])[0].get('track_token') for entry in entries]

        data = {
            "license_token": license_token,
            "media": [{
                "formats": [
                    {"cipher": "BF_CBC_STRIPE", "format": "MP3_128"},
                    {"cipher": "BF_CBC_STRIPE", "format": "MP3_64"}
                ],
                "type": "FULL"}
            ],
            "track_tokens": track_tokens
        }

        self.get_key_dynamically()
        response = self._download_json(self.GET_URL, data_id, data=json.dumps(data).encode('utf-8'))

        for i in range(len(entries)):
            media = response.get('data', [{}])[i].get('media', [{}])[0]
            formats = entries[i].get('formats', [{}])
            format_id = media.get('format')

            for source in media.get('sources', {}):

                format_preference = -1 if '128' in format_id else -2
                format_url = source.get('url')
                format_key = self.compute_blowfish_key(entries[i].get('id'))

                formats.append({
                    'format_id': format_id,
                    'url': format_url,
                    'preference': format_preference,
                    'ext': 'mp3',
                    'key': format_key,
                    'protocol': 'deezer',
                })

            self._sort_formats(formats)

        return entries


class DeezerPodcastExtractor(DeezerBaseInfoExtractor):

    def get_entries(self, data_id, data, json_data):

        #################################
        # GET API TOKEN & LICENSE TOKEN #
        #################################

        api_token, license_token = self.get_api_license_tokens(data_id)

        #################################
        # GET TRACK TOKENS AND PREVIEWS #
        #################################

        url = self.GW_LIGHT_URL + "?" + \
            "api_token=" + api_token + "&" + \
            "method=" + self._METHOD + "&" + \
            "input=3&" + \
            "api_version=1.0&" + \
            "cid=550330597"

        response = self._download_json(url, data_id, data=json.dumps(json_data).encode('utf-8'))

        entries = []
        if ('data' in response.get('results')):
            episodes = traverse_obj(response, ('results', 'data'))
        else:
            episodes = [response.get('results')]

        for episode in episodes:

            entries.append({
                'id': episode.get('EPISODE_ID'),
                'duration': str_to_int(episode.get('DURATION')),
                'title': episode.get('EPISODE_TITLE'),
                'uploader': episode.get('SHOW_NAME'),
                'artist': episode.get('SHOW_NAME'),
                'uploader_id': episode.get('SHOW_ID'),
                'release_timestamp': str_to_int(episode.get('EPISODE_PUBLISHED_TIMESTAMP')),
                'formats': [{
                    'format_id': 'MP3_DIRECT_STREAM',
                    'url': episode.get('EPISODE_DIRECT_STREAM_URL'),
                    'preference': -3,
                    'ext': 'mp3',
                    'track_token': episode.get('TRACK_TOKEN'),
                }]
            })

        return entries


class DeezerArtistIE(DeezerMusicExtractor):
    _VALID_URL = r'https?://(?:www\.)?deezer\.com/(?P<country>..+)/artist/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.deezer.com/fr/artist/1711511',
        'info_dict': {
            'id': '1711511',
            'title': 'Top tracks',
            'uploader': 'Bolivard',
            'thumbnail': r're:^https?://(e-)?cdns-images\.dzcdn\.net/images/artist/.*\.jpg$',
        },
        'playlist_count': 27,
    }
    _API_URL = "https://api.deezer.com/artist/{0}?limit=-1"
    _METHOD = "artist.getTopTrack"

    def _real_extract(self, url):

        artist_id, country, artist_data = self.get_data(url)
        artist_name = artist_data.get('name')
        artist_thumbnail = artist_data.get('picture_medium')

        json_data = {
            'nb': 10000,
            'art_id': artist_id,
            'start': 0
        }
        artist_entries = self.get_entries(artist_id, artist_data, json_data)

        return {
            '_type': 'playlist',
            'id': artist_id,
            'title': 'Top tracks',
            'uploader': artist_name,
            'thumbnail': artist_thumbnail,
            'entries': artist_entries,
        }


class DeezerPlaylistIE(DeezerMusicExtractor):
    _VALID_URL = r'https?://(?:www\.)?deezer\.com/(?P<country>..+)/playlist/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://www.deezer.com/playlist/176747451',
        'info_dict': {
            'id': '176747451',
            'title': 'Best!',
            'uploader': 'Anonymous',
            'thumbnail': r're:^https?://(e-)?cdns-images\.dzcdn\.net/images/cover/.*\.jpg$',
        },
        'playlist_count': 30,
    }
    _API_URL = "https://api.deezer.com/playlist/{0}?limit=-1"
    _METHOD = "playlist.getSongs"

    def _real_extract(self, url):

        playlist_id, country, playlist_data = self.get_data(url)
        playlist_title = playlist_data.get('title')
        playlist_uploader = traverse_obj(playlist_data, ('creator', 'name'))
        playlist_thumbnail = playlist_data.get('picture_medium')

        json_data = {
            'nb': 2000,
            'playlist_id': playlist_id,
            'start': 0
        }
        playlist_entries = self.get_entries(playlist_id, playlist_data, json_data)

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': playlist_title,
            'uploader': playlist_uploader,
            'thumbnail': playlist_thumbnail,
            'entries': playlist_entries,
        }


class DeezerAlbumIE(DeezerMusicExtractor):
    _VALID_URL = r'https?://(?:www\.)?deezer\.com/(?P<country>..+)/album/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.deezer.com/fr/album/67505622',
        'info_dict': {
            'id': '67505622',
            'title': 'Last Week',
            'uploader': 'Home Brew',
            'thumbnail': r're:^https?://(e-)?cdns-images\.dzcdn\.net/images/cover/.*\.jpg$',
        },
        'playlist_count': 7,
    }
    _API_URL = "https://api.deezer.com/album/{0}?limit=-1"
    _METHOD = "song.getListByAlbum"

    def _real_extract(self, url):

        album_id, country, album_data = self.get_data(url)
        album_title = album_data.get('title')
        album_uploader = traverse_obj(album_data, ('artist', 'name'))
        album_thumbnail = album_data.get('cover_medium')

        json_data = {
            'nb': 500,
            'alb_id': album_id,
            'start': 0
        }
        album_entries = self.get_entries(album_id, album_data, json_data)

        return {
            '_type': 'playlist',
            'id': album_id,
            'title': album_title,
            'uploader': album_uploader,
            'thumbnail': album_thumbnail,
            'entries': album_entries,
        }


class DeezerTrackIE(DeezerMusicExtractor):
    _VALID_URL = r'https?://(?:www\.)?deezer\.com/(?P<country>..+)/track/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.deezer.com/fr/track/675631092',
        'info_dict': {
            'id': '675631092',
            'title': 'La vie',
            'uploader': 'Bolivard',
            'thumbnail': r're:^https?://(e-)?cdns-images\.dzcdn\.net/images/cover/.*\.jpg$',
        },
        'playlist_count': 1,
    }
    _API_URL = "https://api.deezer.com/track/{0}?limit=-1"
    _METHOD = "song.getListData"

    def _real_extract(self, url):

        self.get_key_dynamically()

        track_id, country, track_data = self.get_data(url)
        track_title = track_data.get('title')
        track_uploader = traverse_obj(track_data, ('artist', 'name'))
        track_thumbnail = traverse_obj(track_data, ('album', 'cover_medium'))

        json_data = {
            'sng_ids': [track_id]
        }
        track_entries = self.get_entries(track_id, track_data, json_data)

        return {
            '_type': 'playlist',
            'id': track_id,
            'title': track_title,
            'uploader': track_uploader,
            'thumbnail': track_thumbnail,
            'entries': track_entries,
        }


class DeezerEpisodeIE(DeezerPodcastExtractor):
    _VALID_URL = r'https?://(?:www\.)?deezer\.com/(?P<country>..+)/episode/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.deezer.com/fr/episode/432949767',
        'info_dict': {
            'id': '432949767',
            'title': 'FAQ ETH 2.0 : Comment profiter du MERGE ? Tout comprendre sur la MAJ HISTORIQUE',
            'uploader': 'Cryptoast - Bitcoin et Cryptomonnaies',
            'thumbnail': r're:^https?://(e-)?cdns-images\.dzcdn\.net/images/talk/.*\.jpg$',
        },
        'playlist_count': 1,
    }
    _API_URL = "https://api.deezer.com/episode/{0}?limit=-1"
    _METHOD = "episode.getData"

    def _real_extract(self, url):

        episode_id, country, episode_data = self.get_data(url)
        episode_title = episode_data.get('title')
        episode_uploader = traverse_obj(episode_data, ('podcast', 'title'))
        episode_thumbnail = episode_data.get('picture_medium')

        json_data = {
            'episode_id': episode_id
        }
        episode_entries = self.get_entries(episode_id, episode_data, json_data)

        return {
            '_type': 'playlist',
            'id': episode_id,
            'title': episode_title,
            'uploader': episode_uploader,
            'thumbnail': episode_thumbnail,
            'entries': episode_entries,
        }


class DeezerShowIE(DeezerPodcastExtractor):
    _VALID_URL = r'https?://(?:www\.)?deezer\.com/(?P<country>..+)/show/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.deezer.com/fr/show/1805732',
        'info_dict': {
            'id': '1805732',
            'title': 'Cryptoast - Bitcoin et Cryptomonnaies',
            'uploader': 'Cryptoast - Bitcoin et Cryptomonnaies',
            'thumbnail': r're:^https?://(e-)?cdns-images\.dzcdn\.net/images/talk/.*\.jpg$',
        },
        'playlist_count': 129,
    }
    _API_URL = "https://api.deezer.com/podcast/{0}?limit=-1"
    _METHOD = "episode.getListByShow"

    def _real_extract(self, url):

        show_id, country, show_data = self.get_data(url)
        show_title = show_data.get('title')
        show_thumbnail = show_data.get('picture_medium')

        json_data = {
            'nb': 1000,
            'show_id': show_id,
            'start': 0
        }
        show_entries = self.get_entries(show_id, show_data, json_data)

        return {
            '_type': 'playlist',
            'id': show_id,
            'title': show_title,
            'uploader': show_title,
            'thumbnail': show_thumbnail,
            'entries': show_entries,
        }
