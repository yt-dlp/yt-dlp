from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    smuggle_url,
)


class MinistryGridIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ministrygrid\.com/([^/?#]*/)*(?P<id>[^/#?]+)/?(?:$|[?#])'

    _TEST = {
        'url': 'http://www.ministrygrid.com/training-viewer/-/training/t4g-2014-conference/the-gospel-by-numbers-4/the-gospel-by-numbers',
        'md5': '844be0d2a1340422759c2a9101bab017',
        'info_dict': {
            'id': '3453494717001',
            'ext': 'mp4',
            'title': 'The Gospel by Numbers',
            'thumbnail': r're:^https?://.*\.jpg',
            'upload_date': '20140410',
            'description': 'Coming soon from T4G 2014!',
            'uploader_id': '2034960640001',
            'timestamp': 1397145591,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'add_ie': ['TDSLifeway'],
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        portlets = self._parse_json(self._search_regex(
            r'Liferay\.Portlet\.list=(\[.+?\])', webpage, 'portlet list'),
            video_id)
        pl_id = self._search_regex(
            r'getPlid:function\(\){return"(\d+)"}', webpage, 'p_l_id')

        for i, portlet in enumerate(portlets):
            portlet_url = 'http://www.ministrygrid.com/c/portal/render_portlet?p_l_id=%s&p_p_id=%s' % (pl_id, portlet)
            portlet_code = self._download_webpage(
                portlet_url, video_id,
                note='Looking in portlet %s (%d/%d)' % (portlet, i + 1, len(portlets)),
                fatal=False)
            video_iframe_url = self._search_regex(
                r'<iframe.*?src="([^"]+)"', portlet_code, 'video iframe',
                default=None)
            if video_iframe_url:
                return self.url_result(
                    smuggle_url(video_iframe_url, {'force_videoid': video_id}),
                    video_id=video_id)

        raise ExtractorError('Could not find video iframe in any portlets')
