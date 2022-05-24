from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    str_or_none,
    strip_or_none,
    try_get,
    urljoin,
)


class StreetVoiceIE(InfoExtractor):
    _VALID_URL = r'https?://(?:.+?\.)?streetvoice\.com/[^/]+/songs/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://streetvoice.com/skippylu/songs/123688/',
        'md5': '0eb535970629a5195685355f3ed60bfd',
        'info_dict': {
            'id': '123688',
            'ext': 'mp3',
            'title': '流浪',
            'description': 'md5:8eb0bfcc9dcd8aa82bd6efca66e3fea6',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 270,
            'upload_date': '20100923',
            'uploader': 'Crispy脆樂團',
            'uploader_id': '627810',
            'uploader_url': 're:^https?://streetvoice.com/skippylu/',
            'timestamp': 1285261661,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
            'track': '流浪',
            'track_id': '123688',
            'album': '2010',
        }
    }, {
        'url': 'http://tw.streetvoice.com/skippylu/songs/94440/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        song_id = self._match_id(url)
        base_url = 'https://streetvoice.com/api/v4/song/%s/' % song_id
        song = self._download_json(base_url, song_id, query={
            'fields': 'album,comments_count,created_at,id,image,length,likes_count,name,nickname,plays_count,profile,share_count,synopsis,user,username',
        })
        title = song['name']

        formats = []
        for suffix, format_id in [('hls/file', 'hls'), ('file', 'http'), ('file/original', 'original')]:
            f_url = (self._download_json(
                base_url + suffix + '/', song_id,
                'Downloading %s format URL' % format_id,
                data=b'', fatal=False) or {}).get('file')
            if not f_url:
                continue
            f = {
                'ext': 'mp3',
                'format_id': format_id,
                'url': f_url,
                'vcodec': 'none',
            }
            if format_id == 'hls':
                f['protocol'] = 'm3u8_native'
            abr = self._search_regex(r'\.mp3\.(\d+)k', f_url, 'bitrate', default=None)
            if abr:
                abr = int(abr)
                f.update({
                    'abr': abr,
                    'tbr': abr,
                })
            formats.append(f)

        user = song.get('user') or {}
        username = user.get('username')
        get_count = lambda x: int_or_none(song.get(x + '_count'))

        return {
            'id': song_id,
            'formats': formats,
            'title': title,
            'description': strip_or_none(song.get('synopsis')),
            'thumbnail': song.get('image'),
            'duration': int_or_none(song.get('length')),
            'timestamp': parse_iso8601(song.get('created_at')),
            'uploader': try_get(user, lambda x: x['profile']['nickname']),
            'uploader_id': str_or_none(user.get('id')),
            'uploader_url': urljoin(url, '/%s/' % username) if username else None,
            'view_count': get_count('plays'),
            'like_count': get_count('likes'),
            'comment_count': get_count('comments'),
            'repost_count': get_count('share'),
            'track': title,
            'track_id': song_id,
            'album': try_get(song, lambda x: x['album']['name']),
        }
