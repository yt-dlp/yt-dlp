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
        'md5': 'a845a6d1ebd08d80c1035126d49bd6a0',
        'info_dict': {
            'id': '2931166',
            'ext': 'mp4',
            'title': 'Lucky Ali - Kitni Haseen Zindagi',
            'track': 'Kitni Haseen Zindagi',
            'artist': 'Lucky Ali',
            'album': 'Aks',
            'release_year': 2000,
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

        webpage = self._download_webpage(url, video_id)

        info = self._search_json_ld(webpage, video_id)

        m3u8_url = self._download_json(
            'https://www.hungama.com/index.php', video_id,
            data=urlencode_postdata({'content_id': video_id}), headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
            }, query={
                'c': 'common',
                'm': 'get_video_mdn_url',
            })['stream_url']

        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, ext='mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')
        self._sort_formats(formats)

        info.update({
            'id': video_id,
            'formats': formats,
        })
        return info


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
