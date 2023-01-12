from .common import InfoExtractor
from ..utils import remove_start


class PressTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?presstv\.ir/[^/]+/(?P<y>\d+)/(?P<m>\d+)/(?P<d>\d+)/(?P<id>\d+)/(?P<display_id>[^/]+)?'

    _TEST = {
        'url': 'http://www.presstv.ir/Detail/2016/04/09/459911/Australian-sewerage-treatment-facility-/',
        'md5': '5d7e3195a447cb13e9267e931d8dd5a5',
        'info_dict': {
            'id': '459911',
            'display_id': 'Australian-sewerage-treatment-facility-',
            'ext': 'mp4',
            'title': 'Organic mattresses used to clean waste water',
            'upload_date': '20160409',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'md5:20002e654bbafb6908395a5c0cfcd125'
        }
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id') or video_id

        webpage = self._download_webpage(url, display_id)

        # extract video URL from webpage
        video_url = self._hidden_inputs(webpage)['inpPlayback']

        # build list of available formats
        # specified in http://www.presstv.ir/Scripts/playback.js
        base_url = 'http://192.99.219.222:82/presstv'
        _formats = [
            (180, '_low200.mp4'),
            (360, '_low400.mp4'),
            (720, '_low800.mp4'),
            (1080, '.mp4')
        ]

        formats = [{
            'url': base_url + video_url[:-4] + extension,
            'format_id': '%dp' % height,
            'height': height,
        } for height, extension in _formats]

        # extract video metadata
        title = remove_start(
            self._html_search_meta('title', webpage, fatal=True), 'PressTV-')

        thumbnail = self._og_search_thumbnail(webpage)
        description = self._og_search_description(webpage)

        upload_date = '%04d%02d%02d' % (
            int(mobj.group('y')),
            int(mobj.group('m')),
            int(mobj.group('d')),
        )

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'description': description
        }
