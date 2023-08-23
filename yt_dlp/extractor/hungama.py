from .common import InfoExtractor
from ..utils import (
    int_or_none,
    remove_end,
    traverse_obj,
    try_get,
    unified_timestamp,
    url_or_none,
    urlencode_postdata,
)


class HungamaBaseIE(InfoExtractor):
    def _call_api(self, path, content_id, fatal=False):
        return traverse_obj(self._download_json(
            f'https://cpage.api.hungama.com/v2/page/content/{content_id}/{path}/detail',
            content_id, fatal=fatal, query={
                'device': 'web',
                'platform': 'a',
                'storeId': '1',
            }), ('data', {dict})) or {}


class HungamaIE(HungamaBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.|un\.)?hungama\.com/
                        (?:
                            (?:video|movie|short-film)/[^/]+/|
                            tv-show/(?:[^/]+/){2}\d+/episode/[^/]+/
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'http://www.hungama.com/video/krishna-chants/39349649/',
        'md5': '687c5f1e9f832f3b59f44ed0eb1f120a',
        'info_dict': {
            'id': '39349649',
            'ext': 'mp4',
            'title': 'Krishna Chants',
            'description': ' ',
            'upload_date': '20180829',
            'duration': 264,
            'timestamp': 1535500800,
            'view_count': int,
            'thumbnail': 'https://images1.hungama.com/tr:n-a_169_m/c/1/0dc/2ca/39349649/39349649_350x197.jpg?v=8',
            'tags': 'count:6',
        },
    }, {
        'url': 'https://un.hungama.com/short-film/adira/102524179/',
        'md5': '2278463f5dc9db9054d0c02602d44666',
        'info_dict': {
            'id': '102524179',
            'ext': 'mp4',
            'title': 'Adira',
            'description': 'md5:df20cd4d41eabb33634f06de1025a4b4',
            'upload_date': '20230417',
            'timestamp': 1681689600,
            'view_count': int,
            'thumbnail': 'https://images1.hungama.com/tr:n-a_23_m/c/1/197/ac9/102524179/102524179_350x525.jpg?v=1',
            'tags': 'count:7',
        },
    }, {
        'url': 'https://www.hungama.com/movie/kahaani-2/44129919/',
        'only_matching': True,
    }, {
        'url': 'https://www.hungama.com/tv-show/padded-ki-pushup/season-1/44139461/episode/ep-02-training-sasu-pathlaag-karing/44139503/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_json = self._download_json(
            'https://www.hungama.com/index.php', video_id,
            data=urlencode_postdata({'content_id': video_id}), headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
            }, query={
                'c': 'common',
                'm': 'get_video_mdn_url',
            })
        formats = self._extract_m3u8_formats(video_json['stream_url'], video_id, ext='mp4', m3u8_id='hls')
        metadata = self._call_api('movie', video_id)

        return {
            **traverse_obj(metadata, ('head', 'data', {
                'title': ('title', {str}),
                'description': ('misc', 'description', {str}),
                'duration': ('duration', {int}),  # duration in JSON is incorrect if string
                'timestamp': ('releasedate', {unified_timestamp}),
                'view_count': ('misc', 'playcount', {int_or_none}),
                'thumbnail': ('image', {url_or_none}),
                'tags': ('misc', 'keywords', ..., {str}),
            })),
            'id': video_id,
            'formats': formats,
            'subtitles': {
                'en': [{
                    'url': video_json['sub_title'],
                    'ext': 'vtt',
                }]
            } if video_json.get('sub_title') else None,
        }


class HungamaSongIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|un\.)?hungama\.com/song/[^/]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.hungama.com/song/kitni-haseen-zindagi/2931166/',
        'md5': '964f46828e8b250aa35e5fdcfdcac367',
        'info_dict': {
            'id': '2931166',
            'ext': 'mp3',
            'title': 'Lucky Ali - Kitni Haseen Zindagi',
            'track': 'Kitni Haseen Zindagi',
            'artist': 'Lucky Ali',
            'album': None,
            'release_year': 2000,
            'thumbnail': 'https://stat2.hungama.ind.in/assets/images/default_images/da-200x200.png',
        },
    }, {
        'url': 'https://un.hungama.com/song/tum-kya-mile-from-rocky-aur-rani-kii-prem-kahaani/103553672',
        'md5': '964f46828e8b250aa35e5fdcfdcac367',
        'info_dict': {
            'id': '103553672',
            'ext': 'mp3',
            'title': 'md5:5ebeb1e10771b634ce5f700ce68ae5f4',
            'track': 'Tum Kya Mile (From "Rocky Aur Rani Kii Prem Kahaani")',
            'artist': 'Pritam Chakraborty, Arijit Singh, Shreya Ghoshal, Amitabh Bhattacharya',
            'album': 'Tum Kya Mile (From "Rocky Aur Rani Kii Prem Kahaani")',
            'release_year': 2023,
            'thumbnail': 'https://images.hungama.com/c/1/7c2/c7b/103553671/103553671_200x200.jpg',
        },
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        data = self._download_json(
            'https://www.hungama.com/audio-player-data/track/%s' % audio_id,
            audio_id, query={'_country': 'IN'})[0]
        track = data['song_name']
        artist = data.get('singer_name')
        formats = []
        media_json = self._download_json(data.get('file') or data['preview_link'], audio_id)
        media_url = try_get(media_json, lambda x: x['response']['media_url'], str)
        media_type = try_get(media_json, lambda x: x['response']['type'], str)

        if media_url:
            formats.append({
                'url': media_url,
                'ext': media_type,
                'vcodec': 'none',
                'acodec': media_type,
            })

        title = '%s - %s' % (artist, track) if artist else track
        thumbnail = data.get('img_src') or data.get('album_image')

        return {
            'id': audio_id,
            'title': title,
            'thumbnail': thumbnail,
            'track': track,
            'artist': artist,
            'album': data.get('album_name') or None,
            'release_year': int_or_none(data.get('date')),
            'formats': formats,
        }


class HungamaAlbumPlaylistIE(HungamaBaseIE):
    _VALID_URL = r'https?://(?:www\.|un\.)?hungama\.com/(?P<path>playlists|album)/[^/]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.hungama.com/album/bhuj-the-pride-of-india/69481490/',
        'playlist_mincount': 7,
        'info_dict': {
            'id': '69481490',
        },
    }, {
        'url': 'https://www.hungama.com/playlists/hindi-jan-to-june-2021/123063/',
        'playlist_mincount': 33,
        'info_dict': {
            'id': '123063',
        },
    }, {
        'url': 'https://un.hungama.com/album/what-jhumka-%3F-from-rocky-aur-rani-kii-prem-kahaani/103891805/',
        'playlist_mincount': 1,
        'info_dict': {
            'id': '103891805',
        },
    }]

    def _real_extract(self, url):
        playlist_id, path = self._match_valid_url(url).group('id', 'path')
        data = self._call_api(remove_end(path, 's'), playlist_id, fatal=True)

        def entries():
            for song_url in traverse_obj(data, ('body', 'rows', ..., 'data', 'misc', 'share', {url_or_none})):
                yield self.url_result(song_url, HungamaSongIE)

        return self.playlist_result(entries(), playlist_id)
