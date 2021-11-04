from __future__ import unicode_literals

from .common import InfoExtractor


class BreitBartIE(InfoExtractor):
    _VALID_URL = r"https?:\/\/(?:www\.)breitbart.com/videos/v/(?P<id>[^/]+)"
    _TESTS = [
        {
            'url': 'https://www.breitbart.com/videos/v/eaiZjVOn/'
        },
        {
            'url': 'https://www.breitbart.com/videos/v/5cOz1yup/?pl=Ij6NDOji'
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_title = self._og_search_title(
            webpage, default=None) or self._html_search_regex(
            r'(?s)<title>(.*?)</title>', webpage, 'video title')
        video_description = self._og_search_description(webpage)
        video_thumbnail = self._og_search_thumbnail(webpage)

        age_limit = self._rta_search(webpage)
        info_dict = {'id': video_id, 'title': video_title, 'description': video_description,
                     'thumbnail': video_thumbnail, 'age_limit': age_limit,
                     'formats': self._extract_m3u8_formats(f'https://cdn.jwplayer.com/manifests/{video_id}.m3u8',
                                                           video_id, ext='mp4')}

        self._sort_formats(info_dict['formats'])

        return info_dict
