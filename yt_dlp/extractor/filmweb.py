from __future__ import unicode_literals

import re

from .common import InfoExtractor


class FilmwebIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?filmweb\.no/(?P<type>trailere|filmnytt)/article(?P<id>\d+)\.ece'
    _TEST = {
        'url': 'http://www.filmweb.no/trailere/article1264921.ece',
        'md5': 'e353f47df98e557d67edaceda9dece89',
        'info_dict': {
            'id': '13033574',
            'ext': 'mp4',
            'title': 'Det som en gang var',
            'upload_date': '20160316',
            'timestamp': 1458140101,
            'uploader_id': '12639966',
            'uploader': 'Live Roaldset',
        }
    }

    def _real_extract(self, url):
        article_type, article_id = re.match(self._VALID_URL, url).groups()
        if article_type == 'filmnytt':
            webpage = self._download_webpage(url, article_id)
            article_id = self._search_regex(r'data-videoid="(\d+)"', webpage, 'article id')
        embed_code = self._download_json(
            'https://www.filmweb.no/template_v2/ajax/json_trailerEmbed.jsp',
            article_id, query={
                'articleId': article_id,
            })['embedCode']
        iframe_url = self._proto_relative_url(self._search_regex(
            r'<iframe[^>]+src="([^"]+)', embed_code, 'iframe url'))

        return {
            '_type': 'url_transparent',
            'id': article_id,
            'url': iframe_url,
            'ie_key': 'TwentyThreeVideo',
        }
