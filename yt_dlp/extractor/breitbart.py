from __future__ import unicode_literals

from .common import InfoExtractor


class BreitBartIE(InfoExtractor):
    _VALID_URL = r'https?:\/\/(?:www\.)breitbart.com/videos/v/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.breitbart.com/videos/v/5cOz1yup/?pl=Ij6NDOji',
        'md5': '0aa6d1d6e183ac5ca09207fe49f17ade',
        'info_dict': {
            'id': '5cOz1yup',
            'ext': 'mp4',
            'title': 'Watch \u2013 Clyburn: Statues in Congress Have to Go Because they Are Honoring Slavery',
            'description': 'md5:bac35eb0256d1cb17f517f54c79404d5',
            'thumbnail': 'https://cdn.jwplayer.com/thumbs/5cOz1yup-1920.jpg',
            'age_limit': 0,
        }
    }, {
        'url': 'https://www.breitbart.com/videos/v/eaiZjVOn/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = self._extract_m3u8_formats(f'https://cdn.jwplayer.com/manifests/{video_id}.m3u8', video_id, ext='mp4')
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': self._og_search_title(
                webpage, default=None) or self._html_search_regex(
                r'(?s)<title>(.*?)</title>', webpage, 'video title'),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'age_limit': self._rta_search(webpage),
            'formats': formats
        }
