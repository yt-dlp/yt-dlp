import re

from .common import InfoExtractor
from ..utils import ExtractorError


class Vbox7IE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:[^/]+\.)?vbox7\.com/
                        (?:
                            play:|
                            (?:
                                emb/external\.php|
                                player/ext\.swf
                            )\?.*?\bvid=
                        )
                        (?P<id>[\da-fA-F]+)
                    '''
    _GEO_COUNTRIES = ['BG']
    _TESTS = [{
        'url': 'http://vbox7.com/play:0946fff23c',
        'md5': 'a60f9ab3a3a2f013ef9a967d5f7be5bf',
        'info_dict': {
            'id': '0946fff23c',
            'ext': 'mp4',
            'title': 'Борисов: Притеснен съм за бъдещето на България',
            'description': 'По думите му е опасно страната ни да бъде обявена за "сигурна"',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1470982814,
            'upload_date': '20160812',
            'uploader': 'zdraveibulgaria',
        },
        'params': {
            'proxy': '127.0.0.1:8118',
        },
    }, {
        'url': 'http://vbox7.com/play:249bb972c2',
        'md5': '99f65c0c9ef9b682b97313e052734c3f',
        'info_dict': {
            'id': '249bb972c2',
            'ext': 'mp4',
            'title': 'Смях! Чудо - чист за секунди - Скрита камера',
        },
        'skip': 'georestricted',
    }, {
        'url': 'http://vbox7.com/emb/external.php?vid=a240d20f9c&autoplay=1',
        'only_matching': True,
    }, {
        'url': 'http://i49.vbox7.com/player/ext.swf?vid=0946fff23c&autoplay=1',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+src=(?P<q>["\'])(?P<url>(?:https?:)?//vbox7\.com/emb/external\.php.+?)(?P=q)',
            webpage)
        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        video_id = self._match_id(url)

        response = self._download_json(
            'https://www.vbox7.com/ajax/video/nextvideo.php?vid=%s' % video_id,
            video_id)

        if 'error' in response:
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, response['error']), expected=True)

        video = response['options']

        title = video['title']
        video_url = video['src']

        if '/na.mp4' in video_url:
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES)

        uploader = video.get('uploader')

        webpage = self._download_webpage(
            'http://vbox7.com/play:%s' % video_id, video_id, fatal=None)

        info = {}

        if webpage:
            info = self._search_json_ld(
                webpage.replace('"/*@context"', '"@context"'), video_id,
                fatal=False)

        info.update({
            'id': video_id,
            'title': title,
            'url': video_url,
            'uploader': uploader,
            'thumbnail': self._proto_relative_url(
                info.get('thumbnail') or self._og_search_thumbnail(webpage),
                'http:'),
        })
        return info
