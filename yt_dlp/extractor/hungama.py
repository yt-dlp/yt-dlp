import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    try_get,
    urlencode_postdata,
)


class HungamaIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?hungama\.com/
                        (?:
                            (?:video|movie)/[^/]+/|
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
            'description': 'Watch Krishna Chants video now. You can also watch other latest videos only at Hungama',
            'upload_date': '20180829',
            'duration': 264,
            'timestamp': 1535500800,
            'view_count': int,
            'thumbnail': 'https://images.hungama.com/c/1/0dc/2ca/39349649/39349649_700x394.jpg',
        }
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

        json_ld = self._search_json_ld(
            self._download_webpage(url, video_id, fatal=False) or '', video_id, fatal=False)

        return {
            **json_ld,
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
    _VALID_URL = r'https?://(?:www\.)?hungama\.com/song/[^/]+/(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.hungama.com/song/kitni-haseen-zindagi/2931166/',
        'md5': 'd4a6a05a394ad0453a9bea3ca00e6024',
        'info_dict': {
            'id': '2931166',
            'ext': 'mp3',
            'title': 'Lucky Ali - Kitni Haseen Zindagi',
            'track': 'Kitni Haseen Zindagi',
            'artist': 'Lucky Ali',
            'album': None,
            'release_year': 2000,
        }
    }

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


class HungamaAlbumPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hungama\.com/(?:playlists|album)/[^/]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.hungama.com/album/bhuj-the-pride-of-india/69481490/',
        'playlist_mincount': 7,
        'info_dict': {
            'id': '69481490',
        },
    }, {
        'url': 'https://www.hungama.com/playlists/hindi-jan-to-june-2021/123063/',
        'playlist_mincount': 50,
        'info_dict': {
            'id': '123063',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        ptrn = r'<meta[^>]+?property=[\"\']?music:song:url[\"\']?[^>]+?content=[\"\']?([^\"\']+)'
        items = re.findall(ptrn, webpage)
        entries = [self.url_result(item, ie=HungamaSongIE.ie_key()) for item in items]
        return self.playlist_result(entries, video_id)
