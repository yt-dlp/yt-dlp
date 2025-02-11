from .common import InfoExtractor


class MoviezineIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?moviezine\.se/video/(?P<id>[^?#]+)'

    _TEST = {
        'url': 'http://www.moviezine.se/video/205866',
        'info_dict': {
            'id': '205866',
            'ext': 'mp4',
            'title': 'Oculus - Trailer 1',
            'description': 'md5:40cc6790fc81d931850ca9249b40e8a4',
            'thumbnail': r're:http://.*\.jpg',
        },
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)
        jsplayer = self._download_webpage(f'http://www.moviezine.se/api/player.js?video={video_id}', video_id, 'Downloading js api player')

        formats = [{
            'format_id': 'sd',
            'url': self._html_search_regex(r'file: "(.+?)",', jsplayer, 'file'),
            'quality': 0,
            'ext': 'mp4',
        }]

        return {
            'id': video_id,
            'title': self._search_regex(r'title: "(.+?)",', jsplayer, 'title'),
            'thumbnail': self._search_regex(r'image: "(.+?)",', jsplayer, 'image'),
            'formats': formats,
            'description': self._og_search_description(webpage),
        }
